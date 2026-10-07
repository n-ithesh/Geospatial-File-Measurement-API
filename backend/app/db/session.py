"""Database engine, session management, and initialisation.

Usage
-----
- Call ``init_db()`` once at application startup to create tables.
- Use ``get_db()`` as a FastAPI dependency to obtain a ``Session``.
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_connect_args() -> dict:
    """Return driver-specific connect args."""
    if settings.DATABASE_URL.startswith("sqlite"):
        # Needed for SQLite to work across threads (one thread per request)
        return {"check_same_thread": False}
    return {}


engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_get_connect_args(),
    # Pool settings suitable for SQLite; ignored/overridden by Postgres driver
    pool_pre_ping=True,
)


# Enable WAL mode for SQLite to allow concurrent reads during writes
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ANN001
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def init_db() -> None:
    """Create all tables if they do not already exist.

    Safe to call multiple times (idempotent).
    """
    from app.db import models  # noqa: F401 – ensure models are imported before create_all

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised: %s", settings.DATABASE_URL)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request.

    The session is always closed in the ``finally`` block, regardless of
    whether the request succeeds or raises an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
