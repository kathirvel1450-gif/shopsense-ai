"""Transparent inactivity-based churn-risk indicators (not a prediction model)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ChurnRiskThresholds:
    """Business-adjustable inactivity and low-activity thresholds."""
    high_recency_days: int = 90
    medium_recency_days: int = 45
    low_frequency: int = 1
    low_monetary: float = 25.0


def classify_churn_risk(rfm: pd.DataFrame, thresholds: ChurnRiskThresholds | None = None) -> pd.DataFrame:
    """Attach risk level and a human-readable reason for each customer."""
    thresholds = thresholds or ChurnRiskThresholds()
    required = {"customer_id", "recency", "frequency", "monetary"}
    if not required.issubset(rfm.columns):
        raise ValueError(f"RFM data missing columns: {sorted(required - set(rfm.columns))}")
    result = rfm.copy()
    levels: list[str] = []
    reasons: list[str] = []
    for row in result.itertuples(index=False):
        values = row._asdict()
        recency = values["recency"]
        frequency = int(values["frequency"] or 0)
        monetary = float(values["monetary"] or 0)
        if frequency == 0:
            levels.append("No Purchase History")
            reasons.append("No completed orders are present for this customer.")
        elif pd.isna(recency):
            levels.append("Insufficient Date Data")
            reasons.append("Completed order exists, but no valid non-future order date supports a recency calculation.")
        elif recency >= thresholds.high_recency_days:
            levels.append("High")
            reasons.append(f"Last completed purchase was {int(recency)} days before the analysis date (high-risk threshold: {thresholds.high_recency_days}); frequency is {frequency} and monetary total is {monetary:.2f}.")
        elif recency >= thresholds.medium_recency_days:
            levels.append("Medium")
            reasons.append(f"Last completed purchase was {int(recency)} days ago (watch threshold: {thresholds.medium_recency_days}); frequency is {frequency} and monetary total is {monetary:.2f}.")
        elif frequency <= thresholds.low_frequency and monetary <= thresholds.low_monetary:
            levels.append("Medium")
            reasons.append(f"Low activity: {frequency} completed order(s) and {monetary:.2f} total monetary value, below configured activity thresholds.")
        else:
            levels.append("Low")
            reasons.append("Recent purchase activity is within configured inactivity thresholds.")
    result["churn_risk_level"] = levels
    result["churn_risk_reason"] = reasons
    return result


def risk_threshold_report(thresholds: ChurnRiskThresholds | None = None) -> dict[str, Any]:
    """Return the applied heuristic thresholds and model limitation."""
    return {"thresholds": asdict(thresholds or ChurnRiskThresholds()), "method": "inactivity-based heuristic", "is_supervised_prediction": False}
