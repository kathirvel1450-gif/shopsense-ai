"""Dynamic SQLAlchemy schema helpers for source CSV tables."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, MetaData, Table, Text


def normalized_name(name: str) -> str:
    """Normalize a CSV column name to a safe SQLite identifier."""
    source = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(name).strip())
    result = re.sub(r"[^a-zA-Z0-9_]+", "_", source).strip("_").lower()
    if not result or result[0].isdigit():
        result = f"col_{result}"
    return result


def primary_key_column(frame: pd.DataFrame, table_name: str) -> str | None:
    """Select a named identifier candidate; database constraints catch bad values."""
    singular = table_name[:-1] if table_name.endswith("s") else table_name
    preferred = {"id", f"{table_name}_id", f"{singular}_id"}
    candidates = [str(col) for col in frame.columns if normalized_name(str(col)) in preferred]
    candidates += [str(col) for col in frame.columns if normalized_name(str(col)).endswith("_id") and str(col) not in candidates]
    # A named identifier remains a primary-key candidate even when its values
    # are malformed; the DB constraint should reject duplicates/nulls visibly.
    return candidates[0] if candidates else None


def build_tables(frames: dict[str, pd.DataFrame], metadata: MetaData | None = None) -> tuple[MetaData, dict[str, Table], dict[str, str | None]]:
    """Build source-derived tables and supported customer foreign keys."""
    metadata = metadata or MetaData()
    pk_columns = {name: primary_key_column(frame, name) for name, frame in frames.items()}
    tables: dict[str, Table] = {}
    customers_pk = pk_columns.get("customers")
    normalized_customer_pk = normalized_name(customers_pk) if customers_pk else None
    for name, frame in frames.items():
        safe_table = normalized_name(name)
        pk = pk_columns[name]
        cols: list[Column[Any]] = []
        seen: set[str] = set()
        for original in frame.columns:
            safe_col = normalized_name(str(original))
            if safe_col in seen:
                raise ValueError(f"Column name collision after normalization in {name}: {safe_col}")
            seen.add(safe_col)
            dtype = _sql_type(frame[original])
            kwargs: dict[str, Any] = {"nullable": bool(frame[original].isna().any())}
            if original == pk:
                kwargs.update(primary_key=True, nullable=False)
                if isinstance(dtype, BigInteger):
                    dtype = Integer()
            elif name in {"orders", "tickets"} and safe_col == "customer_id" and customers_pk and normalized_customer_pk:
                kwargs["index"] = True
                cols.append(Column(safe_col, dtype, ForeignKey(f"customers.{normalized_customer_pk}"), **kwargs))
                continue
            cols.append(Column(safe_col, dtype, **kwargs))
        tables[name] = Table(safe_table, metadata, *cols)
    return metadata, tables, pk_columns


def _sql_type(series: pd.Series):
    if pd.api.types.is_bool_dtype(series):
        return Boolean()
    if pd.api.types.is_integer_dtype(series):
        return BigInteger()
    if pd.api.types.is_float_dtype(series):
        return Float()
    if pd.api.types.is_datetime64_any_dtype(series):
        return DateTime()
    return Text()
