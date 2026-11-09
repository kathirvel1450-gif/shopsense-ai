"""Configurable, auditable cleaning operations that never mutate raw input."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

GENDER_ALIASES = {"male": "Male", "m": "Male", "man": "Male", "men": "Male", "female": "Female", "f": "Female", "woman": "Female", "women": "Female"}
NUMERIC_HINT = re.compile(r"amount|revenue|price|total|quantity|^qty$|count|age|score|rating|value", re.I)


@dataclass
class CleaningStrategy:
    """Options for deterministic cleaning; unknown columns are preserved."""
    drop_exact_duplicates: bool = True
    city_aliases: dict[str, str] = field(default_factory=dict)
    missing_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    impossible_numeric_min: dict[str, float] = field(default_factory=dict)
    date_columns: list[str] = field(default_factory=list)
    infer_numeric_columns: bool = True


def clean_dataframe(frame: pd.DataFrame, dataset: str, strategy: CleaningStrategy | None = None) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Return a cleaned copy and an operation log; raw frame is never changed."""
    strategy = strategy or CleaningStrategy()
    result = frame.copy(deep=True)
    log: list[dict[str, Any]] = []
    if strategy.drop_exact_duplicates:
        duplicated = int(result.duplicated().sum())
        if duplicated:
            result = result.drop_duplicates(keep="first").copy()
            log.append(_event(dataset, "drop_exact_duplicates", rows_affected=duplicated, details="Removed later copies of exact duplicate rows; first occurrence retained."))
    for column in result.columns:
        normalized = _norm(column)
        if re.search(r"(^|_)gender($|_)", normalized) and not normalized.endswith("_id"):
            before = result[column].copy()
            result[column] = before.map(_normalize_gender)
            changed = int((before.astype("string").fillna("<NA>") != result[column].astype("string").fillna("<NA>")).sum())
            if changed:
                log.append(_event(dataset, "normalize_gender", column=str(column), rows_affected=changed, details="Mapped recognized values to Male/Female; all other non-empty values to Unknown."))
        if "city" in normalized.split("_") and not normalized.endswith("_id"):
            before = result[column].copy()
            aliases = {_norm(k): str(v).strip().title() for k, v in strategy.city_aliases.items()}
            result[column] = before.map(lambda value: _normalize_city(value, aliases))
            changed = int((before.astype("string").fillna("<NA>") != result[column].astype("string").fillna("<NA>")).sum())
            if changed:
                log.append(_event(dataset, "standardize_city", column=str(column), rows_affected=changed, details="Trimmed/case-normalized values; configured aliases applied."))
    for column in result.columns:
        normalized = _norm(column)
        is_date = column in strategy.date_columns or bool(re.search(r"date|time|timestamp|(^|_)at$", normalized))
        if is_date and not pd.api.types.is_datetime64_any_dtype(result[column]):
            before = result[column]
            parsed = pd.to_datetime(before, errors="coerce", format="mixed")
            invalid = int((before.notna() & parsed.isna()).sum())
            result[column] = parsed
            if invalid:
                log.append(_event(dataset, "coerce_invalid_dates", column=str(column), rows_affected=invalid, details="Unparseable non-empty values converted to missing; original remains in raw CSV."))
        if strategy.infer_numeric_columns and NUMERIC_HINT.search(normalized) and not pd.api.types.is_numeric_dtype(result[column]):
            converted = pd.to_numeric(result[column], errors="coerce")
            valid_original = int(result[column].notna().sum())
            if valid_original and int(converted.notna().sum()) / valid_original >= 0.9:
                bad = int((result[column].notna() & converted.isna()).sum())
                result[column] = converted
                log.append(_event(dataset, "coerce_numeric", column=str(column), rows_affected=bad, details="Numeric-looking values converted; unparseable values become missing."))
    for column in result.columns:
        configured_min = strategy.impossible_numeric_min.get(str(column))
        inferred_min = 0 if re.search(r"amount|revenue|price|total|quantity|^qty$|age|count", _norm(column)) else None
        minimum = configured_min if configured_min is not None else inferred_min
        if minimum is not None and pd.api.types.is_numeric_dtype(result[column]):
            invalid_mask = result[column].notna() & (result[column] < minimum)
            count = int(invalid_mask.sum())
            if count:
                result.loc[invalid_mask, column] = np.nan
                log.append(_event(dataset, "null_impossible_numeric", column=str(column), rows_affected=count, details=f"Values below configured/inferred minimum {minimum} set missing; review raw source."))
    for column, rule in strategy.missing_rules.get(dataset, {}).items():
        if column not in result:
            continue
        before_missing = int(result[column].isna().sum())
        action = str(rule.get("action", "preserve"))
        if action == "fill":
            value = rule.get("value")
            if value == "median" and pd.api.types.is_numeric_dtype(result[column]):
                value = result[column].median()
            elif value == "mode":
                modes = result[column].mode(dropna=True)
                value = modes.iloc[0] if not modes.empty else None
            if value is not None:
                result[column] = result[column].fillna(value)
        elif action == "drop_rows":
            removed = int(result[column].isna().sum())
            result = result.loc[result[column].notna()].copy()
            log.append(_event(dataset, "drop_missing_rows", column=column, rows_affected=removed, details="Explicitly configured strategy; removed rows retained in raw CSV."))
            continue
        after_missing = int(result[column].isna().sum()) if column in result else 0
        if before_missing != after_missing:
            log.append(_event(dataset, f"missing_{action}", column=column, rows_affected=before_missing-after_missing, details=f"Configured missing-value action '{action}'."))
    return result, log


def detect_numeric_outliers(frame: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    """Return IQR outlier counts and fences; observations are never removed."""
    result: dict[str, dict[str, float | int]] = {}
    for column in frame.select_dtypes(include="number").columns:
        values = frame[column].dropna()
        if values.empty:
            continue
        q1, q3 = values.quantile([0.25, 0.75])
        spread = q3 - q1
        low, high = float(q1 - 1.5 * spread), float(q3 + 1.5 * spread)
        count = int(((values < low) | (values > high)).sum())
        result[str(column)] = {"outlier_count": count, "lower_fence": low, "upper_fence": high, "removed": 0}
    return result


def _normalize_gender(value: Any) -> Any:
    if pd.isna(value):
        return "Unknown"
    text = str(value).strip()
    if not text:
        return "Unknown"
    return GENDER_ALIASES.get(text.casefold(), "Unknown")


def _normalize_city(value: Any, aliases: dict[str, str]) -> Any:
    if pd.isna(value) or not str(value).strip():
        return value
    text = re.sub(r"\s+", " ", str(value).strip())
    return aliases.get(_norm(text), text.title())


def _norm(value: Any) -> str:
    source = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value).strip())
    return re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")


def _event(dataset: str, operation: str, **kwargs: Any) -> dict[str, Any]:
    return {"dataset": dataset, "operation": operation, **kwargs}
