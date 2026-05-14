"""SQLAlchemy + raw sqlite (for FTS5) bootstrap.

Database backend selection:
  * If `DATABASE_URL` is set in the environment, it is used as-is. Examples:
      sqlite:///./data/app.db
      mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+17+for+SQL+Server
  * Otherwise we default to a local SQLite file at ``settings.db_path``.

The application code is written against SQLAlchemy ORM and stays portable.
The only backend-specific bit is the FTS5 virtual table used for full-text
search; on non-SQLite backends we fall back to a plain ``LIKE`` scan.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from .config import settings


def _build_database_url() -> str:
    explicit = os.getenv("DATABASE_URL", "").strip()
    if explicit:
        return explicit
    return f"sqlite:///{settings.db_path.as_posix()}"


DATABASE_URL = _build_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")


_engine_kwargs = {"echo": False, "future": True, "pool_pre_ping": True}
if IS_SQLITE:
    _engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    _engine_kwargs["pool_size"] = 20
    _engine_kwargs["max_overflow"] = 40
else:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **_engine_kwargs)


@event.listens_for(engine, "connect")
def _on_connect(dbapi_conn, connection_record):  # noqa: D401
    if not IS_SQLITE:
        return
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.execute("PRAGMA busy_timeout=30000;")
    cur.execute("PRAGMA synchronous=NORMAL;")
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
    """Returns a raw sqlite3 connection (used for FTS5 ops). Only valid when
    the active backend is SQLite."""
    if not IS_SQLITE:
        raise RuntimeError("raw_sqlite() is only available on the SQLite backend")
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables (incl. FTS5 virtual table on SQLite)."""
    from . import models  # noqa: F401  Ensure models are imported.

    Base.metadata.create_all(bind=engine)

    if not IS_SQLITE:
        # SQL Server / Postgres: ORM tables are enough; FTS5 isn't applicable.
        return

    # Lightweight schema migration for older SQLite DBs.
    with raw_sqlite() as conn:
        for stmt in [
            "ALTER TABLE documents ADD COLUMN processed_pages INTEGER DEFAULT 0",
        ]:
            try:
                conn.execute(stmt)
                conn.commit()
            except Exception:
                pass

    # FTS5 virtual table for page text. Trigram tokenizer for CJK substring,
    # falling back to unicode61 on older SQLite builds.
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
