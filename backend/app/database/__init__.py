"""Database setup and persistence module."""

from app.database.connection import get_engine

__all__ = ["get_engine"]
