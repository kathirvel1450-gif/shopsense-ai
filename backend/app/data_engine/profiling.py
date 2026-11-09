"""Data quality profiling with suppression for personal information columns."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

SENSITIVE = re.compile(r"(^|_)(id|customer_id|order_id|ticket_id|email|e_mail|phone|mobile|telephone|contact|address|postal|postcode|zip|name|username|token|password|ssn|credit_card|card_number|message|comment|description|notes|body|text|subject)(_|$)", re.I)


def is_sensitive_column(column: str) -> bool:
    """Detect common direct identifiers by normalized column name."""
    source = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(column).strip())
    normalized = re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")
    return bool(SENSITIVE.search(normalized))


def profile_dataframe(frame: pd.DataFrame, name: str = "dataset") -> dict[str, Any]:
    """Summarize shape, schema, nulls, duplicates, distributions, ranges, and stats."""
    columns: dict[str, Any] = {}
    for column in frame.columns:
        series = frame[column]
        missing = int(series.isna().sum())
        sensitive = is_sensitive_column(str(column))
        item: dict[str, Any] = {
            "dtype": str(series.dtype),
            "missing_count": missing,
            "missing_percent": round(missing * 100 / len(frame), 2) if len(frame) else 0.0,
            "unique_count": int(series.nunique(dropna=True)),
            "sensitive_values_suppressed": sensitive,
        }
        if not sensitive and (pd.api.types.is_object_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype) or pd.api.types.is_bool_dtype(series)):
            counts = series.astype("string").fillna("<MISSING>").value_counts(dropna=False)
            high_cardinality = len(counts) > 50 or (len(counts) >= 10 and len(frame) > 0 and len(counts) / len(frame) > 0.5)
            if high_cardinality:
                item["distribution_suppressed"] = True
            else:
                item["distribution"] = [
                    {"value": str(value), "count": int(count), "percent": round(count * 100 / len(frame), 2) if len(frame) else 0.0}
                    for value, count in counts.items()
                ]
        elif pd.api.types.is_numeric_dtype(series) and not sensitive:
            stats = series.describe()
            item["numeric_summary"] = {key: _json_number(value) for key, value in stats.items()}
        if _date_like(series, str(column)) and not sensitive:
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
            valid = parsed.dropna()
            item["date_range"] = {"min": valid.min().isoformat() if not valid.empty else None, "max": valid.max().isoformat() if not valid.empty else None}
        columns[str(column)] = item
    return {
        "dataset": name,
        "rows": int(len(frame)),
        "columns_count": int(len(frame.columns)),
        "columns": list(map(str, frame.columns)),
        "duplicate_rows": int(frame.duplicated().sum()),
        "column_profiles": columns,
    }


def write_profile(profile: dict[str, Any], path: Path) -> None:
    """Write an indented JSON report."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def _date_like(series: pd.Series, name: str) -> bool:
    return pd.api.types.is_datetime64_any_dtype(series) or bool(re.search(r"date|time|_at$|timestamp", name, re.I))


def _json_number(value: Any) -> float | int | None:
    if pd.isna(value):
        return None
    result = float(value)
    return int(result) if result.is_integer() else result
