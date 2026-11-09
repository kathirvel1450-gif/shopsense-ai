"""End-to-end customer intelligence workflow over Phase 3 cleaned CSVs."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from app.customer_intelligence.churn_risk import ChurnRiskThresholds, classify_churn_risk, risk_threshold_report
from app.customer_intelligence.clustering import KMeansConfig, evaluate_kmeans, fit_selected_model, model_metadata, select_k
from app.customer_intelligence.preprocessing import FEATURES, prepare_rfm_features, save_scaler
from app.customer_intelligence.rfm import calculate_rfm
from app.customer_intelligence.segmentation import label_segments
from app.customer_intelligence.visualization import generate_customer_visualizations
from app.data_engine.pipeline import configured_paths, project_root


def run_customer_intelligence(
    cleaned_dir: Path | None = None,
    outputs_dir: Path | None = None,
    analysis_reference_date: str | pd.Timestamp | None = None,
    completed_statuses: Iterable[str] = ("completed", "complete", "delivered"),
    kmeans_config: KMeansConfig | None = None,
    risk_thresholds: ChurnRiskThresholds | None = None,
) -> dict[str, Any]:
    """Run RFM, K-Means selection, behavior labels, and inactivity risk rules."""
    root = project_root()
    load_dotenv(root / ".env", override=False)
    paths = configured_paths()
    cleaned_dir = Path(cleaned_dir or paths["processed"])
    outputs_dir = Path(outputs_dir or paths["outputs"])
    report_dir = outputs_dir / "reports"
    model_dir = outputs_dir / "models"
    artifact_dir = outputs_dir / "customer_intelligence"
    charts_dir = outputs_dir / "visualizations" / "customer_intelligence"
    for directory in (report_dir, artifact_dir, charts_dir):
        directory.mkdir(parents=True, exist_ok=True)
    customer_path, order_path = cleaned_dir / "customers.csv", cleaned_dir / "orders.csv"
    missing = [name for name, path in (("customers.csv", customer_path), ("orders.csv", order_path)) if not path.is_file()]
    if missing:
        report = _missing_report(missing)
        _write_json(report_dir / "customer_intelligence_report.json", report)
        return report
    try:
        customers = pd.read_csv(customer_path)
        orders = pd.read_csv(order_path)
        effective_reference = analysis_reference_date or os.getenv("RFM_ANALYSIS_DATE")
        rfm, rfm_report = calculate_rfm(customers, orders, effective_reference, completed_statuses)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError, ValueError, TypeError) as exc:
        report = {"status": "invalid_data", "message": f"Could not calculate RFM from cleaned CSVs: {type(exc).__name__}: {exc}", "missing_files": [], "customer_count": None, "rfm": None, "model_evaluation": [], "selected_k": None}
        _write_json(report_dir / "customer_intelligence_report.json", report)
        return report

    eligible_ids, scaled, scaler, preprocessing_report = prepare_rfm_features(rfm)
    model_dir.mkdir(parents=True, exist_ok=True)
    scaler_path = save_scaler(scaler, model_dir / "rfm_standard_scaler.joblib") if len(eligible_ids) else None
    config = kmeans_config or KMeansConfig()
    evaluations, models = evaluate_kmeans(scaled, config)
    selection = select_k(evaluations, config)
    selected_model = fit_selected_model(models, selection["selected_k"])
    rfm["cluster_id"] = pd.Series(pd.NA, index=rfm.index, dtype="Int64")
    if selected_model is not None:
        assignments = pd.DataFrame({"customer_id": eligible_ids["customer_id"].to_numpy(), "cluster_id": selected_model.labels_})
        cluster_map = assignments.set_index("customer_id")["cluster_id"]
        rfm["cluster_id"] = rfm["customer_id"].map(cluster_map).astype("Int64")
    segmented, cluster_profiles = label_segments(rfm)
    risk = classify_churn_risk(segmented, risk_thresholds)
    risk_report = risk_threshold_report(risk_thresholds)
    risk_report["note"] = "These are transparent inactivity heuristics, not a supervised churn prediction model."
    report_stats = _rfm_summary(risk)
    visualization_report = generate_customer_visualizations(risk, scaled if len(eligible_ids) else None, evaluations, charts_dir)

    rfm_file = artifact_dir / "customer_rfm.csv"
    segments_file = artifact_dir / "customer_segments.csv"
    risk.to_csv(segments_file, index=False)
    risk[["customer_id", "recency", "frequency", "monetary"]].to_csv(rfm_file, index=False)
    model_path = None
    if selected_model is not None:
        model_path_obj = model_dir / "rfm_kmeans.joblib"
        joblib.dump({"model": selected_model, "features": FEATURES, "selected_k": selection["selected_k"], "random_state": config.random_state, "n_init": config.n_init}, model_path_obj)
        model_path = str(model_path_obj)
    report = {
        "status": "complete" if selected_model is not None else "insufficient_data_for_clustering",
        "message": "RFM calculated from cleaned customer/order files; clustering is unsupervised and churn risk is heuristic.",
        "data_source": {"cleaned_directory": str(cleaned_dir), "customers_file": "customers.csv", "orders_file": "orders.csv"},
        "customer_count": int(len(risk)), "rfm": rfm_report, "rfm_summary": report_stats,
        "preprocessing": preprocessing_report, "kmeans_config": model_metadata(config),
        "model_evaluation": evaluations, "selection": selection, "selected_k": selection["selected_k"],
        "cluster_profiles": cluster_profiles, "churn_risk": {**risk_report, "distribution": _count_values(risk["churn_risk_level"])},
        "visualizations": {"chart_count": visualization_report["chart_count"], "charts": [{"chart": item["chart"], "title": item["title"]} for item in visualization_report["charts"]]},
        "artifacts": {"rfm_csv": str(rfm_file), "customer_segments_csv": str(segments_file), "scaler": scaler_path, "kmeans_model": model_path},
        "limitations": ["K-Means segment labels describe observed RFM clusters only.", "Churn risk is an inactivity heuristic, not a supervised prediction.", "Customer IDs are kept in local artifacts and omitted from aggregate APIs."],
    }
    _write_json(report_dir / "customer_intelligence_report.json", report)
    return report


def _missing_report(missing: list[str]) -> dict[str, Any]:
    return {
        "status": "missing_inputs",
        "message": "Real customer segmentation is pending cleaned trainer data from Phase 3.",
        "missing_files": missing, "customer_count": None, "rfm": None,
        "model_evaluation": [], "selection": {"selected_k": None, "reason": "No cleaned customer/order data was available."},
        "selected_k": None, "visualizations": {"chart_count": 0, "charts": []},
        "churn_risk_method": "inactivity-based heuristic; not a supervised churn prediction model",
    }


def _rfm_summary(rfm: pd.DataFrame) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for feature in ("recency", "frequency", "monetary"):
        values = pd.to_numeric(rfm[feature], errors="coerce").dropna()
        summary[feature] = {"count": int(values.count()), "mean": _number(values.mean()), "median": _number(values.median()), "min": _number(values.min()), "max": _number(values.max())}
    summary["customers_without_completed_orders"] = int(rfm["frequency"].eq(0).sum())
    return summary


def _count_values(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts(dropna=False).items()}


def _number(value: Any) -> float | None:
    return float(value) if pd.notna(value) and np.isfinite(value) else None


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
