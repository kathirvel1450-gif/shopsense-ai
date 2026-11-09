"""Persistence and database validation for ingested DataFrames."""
from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import MetaData, inspect, text
from sqlalchemy.engine import Engine

from app.database.models import build_tables, normalized_name, primary_key_column


def replace_datasets(engine: Engine, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Replace imported tables transactionally and return inserted row counts."""
    metadata = MetaData()
    metadata, tables, pks = build_tables(frames, metadata)
    with engine.begin() as connection:
        metadata.drop_all(connection, checkfirst=True)
        metadata.create_all(connection)
        for name, frame in frames.items():
            prepared = frame.copy()
            prepared.columns = [normalized_name(str(column)) for column in prepared.columns]
            prepared.to_sql(tables[name].name, connection, if_exists="append", index=False)
    return {"tables": {name: {"table": tables[name].name, "rows_inserted": int(len(frame)), "primary_key": pks[name]} for name, frame in frames.items()}}


def database_statistics(engine: Engine) -> dict[str, Any]:
    """Report table row counts and column names without returning row contents."""
    inspector = inspect(engine)
    tables: dict[str, Any] = {}
    with engine.connect() as connection:
        for name in inspector.get_table_names():
            tables[name] = {"rows": int(connection.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar_one()), "columns": [column["name"] for column in inspector.get_columns(name)]}
    return {"database": engine.url.database, "tables": tables, "table_count": len(tables)}


def validate_database(engine: Engine) -> dict[str, Any]:
    """Validate table row counts, primary keys, and SQLite foreign-key integrity."""
    stats = database_statistics(engine)
    violations: list[dict[str, Any]] = []
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            violations = [dict(row._mapping) for row in connection.execute(text("PRAGMA foreign_key_check"))]
    pk_report = {}
    inspector = inspect(engine)
    with engine.connect() as connection:
        for table in stats["tables"]:
            pk = inspector.get_pk_constraint(table).get("constrained_columns", [])
            pk_report[table] = pk
            for column in pk:
                duplicate_count = connection.execute(text(f'SELECT COUNT(*) FROM (SELECT "{column}" FROM "{table}" GROUP BY "{column}" HAVING COUNT(*) > 1)')).scalar_one()
                if duplicate_count:
                    violations.append({"table": table, "column": column, "duplicate_key_groups": int(duplicate_count)})
    return {"valid": not violations, "stats": stats, "primary_keys": pk_report, "foreign_key_violations": violations}
