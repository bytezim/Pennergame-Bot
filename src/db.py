"""
Database configuration and session management.

Optimizations:
- Connection pooling with proper limits
- Thread-safe context manager
- Automatic session cleanup
- WAL mode for better concurrency
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

# SQLite optimization: Use WAL mode for better concurrency
DB_URL = "sqlite:///data.db"

# Connection pooling configuration
# StaticPool for SQLite to maintain single connection in dev
# Use QueuePool in production with proper limits
engine = create_engine(
    DB_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # 30s timeout instead of default 5s
    },
    poolclass=StaticPool,  # Single connection pool for SQLite
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before using
)


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


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
