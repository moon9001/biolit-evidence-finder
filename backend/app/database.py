"""SQLAlchemy + raw sqlite (for FTS5) bootstrap."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from .config import settings


SQLITE_URL = f"sqlite:///{settings.db_path.as_posix()}"

engine = create_engine(
    SQLITE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_sqlite_features(dbapi_conn, connection_record):  # noqa: D401
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def raw_sqlite() -> sqlite3.Connection:
    """Returns a raw sqlite3 connection (used for FTS5 ops)."""
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables (incl. FTS5 virtual table)."""
    from . import models  # noqa: F401  Ensure models are imported.

    Base.metadata.create_all(bind=engine)

    # FTS5 virtual table for page text. SQLAlchemy can't easily model this.
    # `trigram` tokenizer works well for CJK substring search and falls back
    # gracefully for ASCII; older SQLite builds without trigram are handled
    # by retrying with `unicode61`.
    with raw_sqlite() as conn:
        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                    page_id UNINDEXED,
                    document_id UNINDEXED,
                    page_number UNINDEXED,
                    text,
                    tokenize = 'trigram'
                );
                """
            )
        except Exception:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                    page_id UNINDEXED,
                    document_id UNINDEXED,
                    page_number UNINDEXED,
                    text,
                    tokenize = 'unicode61 remove_diacritics 2'
                );
                """
            )
        conn.commit()
