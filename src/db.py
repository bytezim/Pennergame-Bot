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
    if hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


DATA_DIR = get_data_dir()
DB_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)


def close_db_connection():
    import gc
    import time
    import sqlite3

    try:
        engine.dispose()
    except Exception as e:
        logger.error("Error disposing engine: %s", e)
    gc.collect()
    time.sleep(0.1)
    db_file = get_data_dir() / DB_PATH
    try:
        con = sqlite3.connect(str(db_file), timeout=5)
        try:
            con.execute("PRAGMA busy_timeout = 3000")
            result = con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            logger.debug("WAL checkpoint result: %s", result)
        finally:
            con.close()
    except Exception as e:
        logger.error("Error during WAL checkpoint: %s", e)
    if sys.platform == "win32":
        gc.collect()
        time.sleep(0.2)
        for suffix in ("-wal", "-shm"):
            path = Path(str(db_file) + suffix)
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)
Base = declarative_base()


@contextmanager
def get_session() -> Generator[Session, None, None]:
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
    if sys.platform == "win32":
        try:
            db_path = DATA_DIR / DB_PATH
            wal_path = db_path.with_suffix(db_path.suffix + "-wal")
            shm_path = db_path.with_suffix(db_path.suffix + "-shm")
            for path in [wal_path, shm_path]:
                if path.exists():
                    try:
                        path.unlink()
                        logger.debug("[db] Cleaned up stale file: %s", path.name)
                    except Exception as e:
                        logger.debug(
                            "[db] Could not remove stale file %s: %s", path.name, e
                        )
        except Exception as e:
            logger.debug("[db] Error during WAL cleanup: %s", e)


def init_db() -> None:
    _cleanup_stale_wal_files()
    Base.metadata.create_all(bind=engine, checkfirst=True)
    try:
        _migrate_schema()
    except Exception:
        pass


def _migrate_schema() -> None:
    inspector = inspect(engine)
    if "bot_config" in inspector.get_table_names():
        existing = {c["name"] for c in inspector.get_columns("bot_config")}
        to_add = {
            "is_running": "BOOLEAN DEFAULT 0 NOT NULL",
            "last_started": "DATETIME",
            "last_stopped": "DATETIME",
            "bottles_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "bottles_duration_minutes": "INTEGER DEFAULT 60 NOT NULL",
            "bottles_pause_minutes": "INTEGER DEFAULT 1 NOT NULL",
            "bottles_autosell_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "bottles_min_price": "INTEGER DEFAULT 25 NOT NULL",
            "training_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "training_skills": "VARCHAR DEFAULT '[\"att\", \"def\", \"agi\"]' NOT NULL",
            "training_att_max_level": "INTEGER DEFAULT 999 NOT NULL",
            "training_def_max_level": "INTEGER DEFAULT 999 NOT NULL",
            "training_agi_max_level": "INTEGER DEFAULT 999 NOT NULL",
            "training_pause_minutes": "INTEGER DEFAULT 1 NOT NULL",
            "training_autodrink_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "training_target_promille": "FLOAT DEFAULT 3.5 NOT NULL",
            "fight_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "bottles_next_run": "DATETIME",
            "training_next_run": "DATETIME",
            "fight_next_run": "DATETIME",
            "fight_pause_minutes": "INTEGER DEFAULT 1 NOT NULL",
            "rotation_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "rotation_start_with": "VARCHAR DEFAULT 'bottles' NOT NULL",
        }
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                for name, type_decl in to_add.items():
                    if name not in existing:
                        conn.execute(
                            text(
                                f"ALTER TABLE bot_config ADD COLUMN {name} {type_decl}"
                            )
                        )
                transaction.commit()
            except Exception as e:
                transaction.rollback()
                logger.warning(
                    "[db.migrate] Failed to add column(s) to bot_config: %s", e
                )
    if "bot_activities" in inspector.get_table_names():
        existing = {c["name"] for c in inspector.get_columns("bot_activities")}
        to_add = {"was_interrupted": "BOOLEAN DEFAULT 0"}
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                for name, type_decl in to_add.items():
                    if name not in existing:
                        conn.execute(
                            text(
                                f"ALTER TABLE bot_activities ADD COLUMN {name} {type_decl}"
                            )
                        )
                transaction.commit()
            except Exception as e:
                transaction.rollback()
                logger.warning(
                    "[db.migrate] Failed to add column(s) to bot_activities: %s", e
                )


atexit.register(close_db_connection)
