"""
Database configuration and session management.

Optimizations:
- Connection pooling with proper limits
- Thread-safe context manager
- Automatic session cleanup
- WAL mode for better concurrency
"""

import sys
import atexit
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from .constants import DB_PATH

logger = logging.getLogger(__name__)


def get_data_dir() -> Path:
    """Get the data directory for storing database.
    
    In development mode: uses the project directory.
    In PyInstaller bundle mode: uses the directory where the exe is located.
    """
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle - use exe directory
        return Path(sys.executable).parent
    else:
        # Development mode - use project directory
        return Path(__file__).parent.parent


# Get data directory for database
DATA_DIR = get_data_dir()

# SQLite optimization: Use WAL mode for better concurrency
DB_URL = f"sqlite:///{DB_PATH}"

# Connection pooling configuration
# StaticPool for SQLite to maintain single connection in dev
# Use QueuePool in production with proper limits
engine = create_engine(
    DB_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)


def close_db_connection():
    """Properly close database connection and perform WAL checkpoint.
    
    This function should be called on application shutdown to ensure
    all data is written to the main database file and the WAL/shm files
    are cleaned up properly.
    
    Must be called AFTER the backend server thread has fully stopped,
    so that all SQLAlchemy connections are released before checkpointing.
    """
    import gc
    import time
    import sqlite3

    # Step 1: Dispose the SQLAlchemy engine pool - closes all pooled connections
    try:
        engine.dispose()
    except Exception as e:
        logger.error("Error disposing engine: %s", e)

    # Step 2: Force GC to release any lingering Python-held connections
    gc.collect()
    time.sleep(0.1)

    # Step 3: Open a direct sqlite3 connection (bypasses SQLAlchemy pool entirely)
    # and run PRAGMA wal_checkpoint(TRUNCATE) to merge WAL into the main DB file.
    # TRUNCATE resets the WAL file to zero length on success.
    db_file = get_data_dir() / DB_PATH
    try:
        con = sqlite3.connect(str(db_file), timeout=5)
        try:
            # busy_timeout gives other connections a chance to finish
            con.execute("PRAGMA busy_timeout = 3000")
            result = con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            # result = (busy, log, checkpointed); busy==0 means no active writers
            logger.debug("WAL checkpoint result: %s", result)
        finally:
            con.close()
    except Exception as e:
        logger.error("Error during WAL checkpoint: %s", e)

    # Step 4: On Windows, try to remove WAL/SHM files if they still exist
    # (empty WAL files left by TRUNCATE checkpoint are harmless but tidy to remove)
    if sys.platform == 'win32':
        gc.collect()
        time.sleep(0.2)
        for suffix in ('-wal', '-shm'):
            path = Path(str(db_file) + suffix)
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass  # File may still be locked; SQLite will clean it on next open


# Enable WAL mode for SQLite (better concurrency)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes
    cursor.execute("PRAGMA foreign_keys=ON")  # Enforce FK constraints
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Prevent lazy loading issues
)

Base = declarative_base()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Thread-safe context manager for database sessions.

    Usage:
        with get_session() as session:
            user = session.query(User).first()
            # ... do work ...
        # Session automatically committed and closed

    Yields:
        Session: SQLAlchemy session

    Raises:
        Exception: Rolls back transaction on error
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _cleanup_stale_wal_files() -> None:
    """Clean up stale WAL and SHM files from previous crashes.

    This prevents accumulation of temporary files when the application
    doesn't shut down cleanly.
    """
    if sys.platform == 'win32':
        try:
            db_path = DATA_DIR / DB_PATH
            wal_path = db_path.with_suffix(db_path.suffix + '-wal')
            shm_path = db_path.with_suffix(db_path.suffix + '-shm')

            for path in [wal_path, shm_path]:
                if path.exists():
                    try:
                        path.unlink()
                        logger.debug("[db] Cleaned up stale file: %s", path.name)
                    except Exception as e:
                        logger.debug("[db] Could not remove stale file %s: %s", path.name, e)
        except Exception as e:
            logger.debug("[db] Error during WAL cleanup: %s", e)


def init_db() -> None:
    """Initialize database tables."""
    # Clean up any leftover WAL/SHM files from previous crashes
    _cleanup_stale_wal_files()

    # Use checkfirst=True to avoid errors if tables already exist
    Base.metadata.create_all(bind=engine, checkfirst=True)
    # After creating tables, perform lightweight schema migrations
    try:
        _migrate_schema()
    except Exception:
        # Migration is best-effort - don't crash startup on failure
        pass


def _migrate_schema() -> None:
    """Perform small, safe schema migrations for older databases.

    This adds missing nullable DATETIME columns used for scheduler persistence.
    It is intentionally minimal and uses ALTER TABLE ADD COLUMN which
    is supported by SQLite and is safe for adding nullable columns.
    """
    inspector = inspect(engine)

    # Migrate bot_config table
    if "bot_config" in inspector.get_table_names():
        existing = {c["name"] for c in inspector.get_columns("bot_config")}

        to_add = {
            "bottles_next_run": "DATETIME",
            "training_next_run": "DATETIME",
            "fight_next_run": "DATETIME",
        }

        # Use a transaction and commit for DDL changes
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                for name, type_decl in to_add.items():
                    if name not in existing:
                        conn.execute(text(f"ALTER TABLE bot_config ADD COLUMN {name} {type_decl}"))
                transaction.commit()
            except Exception as e:
                transaction.rollback()
                logger.warning("[db.migrate] Failed to add column(s) to bot_config: %s", e)

    # Migrate bot_activities table
    if "bot_activities" in inspector.get_table_names():
        existing = {c["name"] for c in inspector.get_columns("bot_activities")}

        to_add = {
            "was_interrupted": "BOOLEAN DEFAULT 0",
        }

        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                for name, type_decl in to_add.items():
                    if name not in existing:
                        conn.execute(text(f"ALTER TABLE bot_activities ADD COLUMN {name} {type_decl}"))
                transaction.commit()
            except Exception as e:
                transaction.rollback()
                logger.warning("[db.migrate] Failed to add column(s) to bot_activities: %s", e)


# Register cleanup function to run on application exit
# This ensures WAL checkpoint is performed and connections are properly closed
atexit.register(close_db_connection)
