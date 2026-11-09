"""SQLAlchemy engine creation with a configurable local SQLite default."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from dotenv import load_dotenv


def default_database_url() -> str:
    """Use DATABASE_URL or a project-root shopsense.db file."""
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(project_root / ".env", override=False)
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured
    return f"sqlite:///{(project_root / 'shopsense.db').as_posix()}"


def get_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine; SQLite foreign keys are enforced."""
    url = database_url or default_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, future=True, connect_args=connect_args)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine
