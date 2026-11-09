"""RFM feature validation, StandardScaler fitting, and ID separation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

FEATURES = ["recency", "frequency", "monetary"]


def prepare_rfm_features(rfm: pd.DataFrame, scaler: StandardScaler | None = None) -> tuple[pd.DataFrame, np.ndarray, StandardScaler, dict[str, Any]]:
    """Return eligible IDs separately from scaled numeric RFM feature rows."""
    missing = [column for column in ["customer_id", *FEATURES] if column not in rfm.columns]
    if missing:
        raise ValueError(f"RFM input is missing required columns: {missing}")
    candidate = rfm[["customer_id", *FEATURES]].copy()
    for feature in FEATURES:
        candidate[feature] = pd.to_numeric(candidate[feature], errors="coerce")
    numeric = candidate[FEATURES].replace([np.inf, -np.inf], np.nan)
    valid_mask = numeric.notna().all(axis=1) & numeric.ge(0).all(axis=1)
    eligible = candidate.loc[valid_mask, ["customer_id"]].reset_index(drop=True)
    clean_features = numeric.loc[valid_mask].reset_index(drop=True)
    fitted_scaler = scaler or StandardScaler()
    if len(clean_features):
        scaled = fitted_scaler.fit_transform(clean_features) if scaler is None else fitted_scaler.transform(clean_features)
    else:
        scaled = np.empty((0, len(FEATURES)), dtype=float)
    report = {
        "feature_columns": FEATURES.copy(), "input_customers": int(len(rfm)),
        "eligible_for_clustering": int(len(eligible)), "excluded_invalid_or_missing_features": int(len(rfm) - len(eligible)),
        "customers_without_recency_excluded_from_clustering": int(rfm["recency"].isna().sum()),
    }
    return eligible, scaled, fitted_scaler, report


def save_scaler(scaler: StandardScaler, path: Path) -> str:
    """Persist the fitted scaler artifact and return its path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, path)
    return str(path)
