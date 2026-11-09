"""Privacy-preserving aggregate endpoints for customer intelligence."""
import json
from typing import Any

from fastapi import APIRouter

from app.customer_intelligence.pipeline import run_customer_intelligence
from app.data_engine.pipeline import configured_paths

router = APIRouter(prefix="/customers", tags=["customer intelligence"])


def _customer_report() -> dict[str, Any]:
    """Read a fresh aggregate report or compute one from current cleaned files."""
    paths = configured_paths()
    report_path = paths["outputs"] / "reports" / "customer_intelligence_report.json"
    source_paths = [paths["processed"] / "customers.csv", paths["processed"] / "orders.csv"]
    if report_path.is_file() and report_path.stat().st_mtime >= max((p.stat().st_mtime for p in source_paths if p.is_file()), default=0):
        try:
            return json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return run_customer_intelligence()


@router.get("/rfm")
def customers_rfm() -> dict[str, Any]:
    """Return aggregate RFM statistics; never return customer-level rows."""
    report = _customer_report()
    return {"status": report.get("status"), "customer_count": report.get("customer_count"), "reference_date": (report.get("rfm") or {}).get("analysis_reference_date"), "rfm_summary": report.get("rfm_summary"), "missing_files": report.get("missing_files", [])}


@router.get("/segments")
def customers_segments() -> dict[str, Any]:
    """Return cluster profiles and counts without customer IDs."""
    report = _customer_report()
    return {"status": report.get("status"), "selected_k": report.get("selected_k"), "segments": report.get("cluster_profiles", []), "missing_files": report.get("missing_files", [])}


@router.get("/churn-risk")
def customers_churn_risk() -> dict[str, Any]:
    """Return aggregate heuristic risk counts and applied thresholds."""
    report = _customer_report()
    return {"status": report.get("status"), "churn_risk": report.get("churn_risk"), "method": report.get("churn_risk_method", "inactivity-based heuristic; not a supervised churn prediction model"), "missing_files": report.get("missing_files", [])}


@router.get("/model-evaluation")
def customers_model_evaluation() -> dict[str, Any]:
    """Return K-means evaluation metrics and the documented K selection."""
    report = _customer_report()
    return {"status": report.get("status"), "kmeans_config": report.get("kmeans_config"), "evaluations": report.get("model_evaluation", []), "selection": report.get("selection"), "selected_k": report.get("selected_k"), "missing_files": report.get("missing_files", [])}


@router.get("/summary")
def customers_summary() -> dict[str, Any]:
    """Return privacy-preserving customer intelligence dashboard totals."""
    report = _customer_report()
    return {
        "status": report.get("status"), "customer_count": report.get("customer_count"),
        "completed_customers": (report.get("rfm") or {}).get("completed_customers"),
        "customers_without_completed_orders": (report.get("rfm") or {}).get("customers_without_completed_orders"),
        "selected_k": report.get("selected_k"),
        "segment_count": len(report.get("cluster_profiles", [])),
        "segment_counts": [{"segment_name": item["segment_name"], "customer_count": item["customer_count"]} for item in report.get("cluster_profiles", [])],
        "churn_risk_distribution": (report.get("churn_risk") or {}).get("distribution", {}),
        "visualization_count": (report.get("visualizations") or {}).get("chart_count", 0),
        "missing_files": report.get("missing_files", []),
        "churn_risk_note": "Inactivity-based heuristic; not a supervised churn prediction model.",
    }
