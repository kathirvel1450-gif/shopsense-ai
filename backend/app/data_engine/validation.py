"""Dataset and database validation summaries."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.data_engine.cleaning import detect_numeric_outliers
from app.database.models import primary_key_column


def validate_dataframe(name: str, frame: pd.DataFrame) -> dict[str, Any]:
    """Check generic schema quality without assuming trainer-specific columns."""
    pk = primary_key_column(frame, name)
    return {
        "dataset": name,
        "valid": True,
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "empty_column_names": [str(column) for column in frame.columns if not str(column).strip()],
        "duplicate_rows": int(frame.duplicated().sum()),
        "candidate_primary_key": pk,
        "candidate_primary_key_nulls": int(frame[pk].isna().sum()) if pk else None,
        "outliers": detect_numeric_outliers(frame),
    }


def relationship_candidates(frames: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    """Find plausible dataset relationships based on matching *_id columns."""
    candidates = []
    if "customers" not in frames:
        return candidates
    customer_pk = primary_key_column(frames["customers"], "customers")
    if not customer_pk:
        return candidates
    source = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", customer_pk.strip())
    key = re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")
    for child in ("orders", "tickets"):
        if child in frames and key in [re.sub(r"[^a-z0-9]+", "_", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(col).strip()).lower()).strip("_") for col in frames[child].columns]:
            candidates.append({"parent_table": "customers", "parent_column": customer_pk, "child_table": child, "child_column": customer_pk})
    return candidates
