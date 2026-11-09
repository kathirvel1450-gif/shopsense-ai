"""Ticket batch processing for Phase 3 cleaned ticket CSVs."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

from app.data_engine.pipeline import configured_paths
from app.guardrails.model_gateway import GuardrailGateway


def map_ticket_columns(frame: pd.DataFrame) -> dict[str, str | None]:
    """Map common ticket schema aliases against the actual observed headers."""
    normalized = {_normalize(str(column)): str(column) for column in frame.columns}
    aliases = {
        "ticket_id": ("ticket_id", "ticketid", "case_id", "id"),
        "customer_id": ("customer_id", "customerid", "customer_key"),
        "order_id": ("order_id", "orderid", "order_number"),
        "ticket_text": ("ticket_text", "ticket_description", "description", "message", "body", "text", "subject"),
        "created_at": ("created_at", "created_date", "ticket_date", "date", "timestamp"),
        "ticket_status": ("ticket_status", "status", "case_status"),
        "ticket_category": ("ticket_category", "category", "type"),
    }
    result = {field: next((normalized[name] for name in names if name in normalized), None) for field, names in aliases.items()}
    if not result["ticket_text"]:
        raise ValueError(f"Could not map ticket text column. Available columns: {list(map(str, frame.columns))}")
    return result


def run_ticket_pipeline(
    cleaned_dir: Path | None = None,
    outputs_dir: Path | None = None,
    method: str | None = None,
    gateway: GuardrailGateway | None = None,
) -> dict[str, Any]:
    """Validate, mask, classify, prioritize, and route each cleaned ticket safely."""
    paths = configured_paths()
    cleaned_dir = Path(cleaned_dir or paths["processed"])
    outputs_dir = Path(outputs_dir or paths["outputs"])
    report_dir = outputs_dir / "reports"
    results_dir = outputs_dir / "ticket_intelligence"
    report_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    source = cleaned_dir / "tickets.csv"
    if not source.is_file():
        report = {
            "status": "missing_inputs", "message": "Ticket processing is pending the Phase 3 cleaned tickets.csv file.",
            "missing_files": ["tickets.csv"], "ticket_rows": None, "classified_count": 0,
            "rejected_count": 0, "classification_accuracy": None,
            "classification_accuracy_note": "No labeled evaluation dataset was supplied; accuracy is not reported.",
            "category_counts": {}, "priority_counts": {}, "team_counts": {}, "pii_mask_counts": {},
        }
        _write_json(report_dir / "ticket_intelligence_report.json", report)
        return report
    try:
        tickets = pd.read_csv(source)
        columns = map_ticket_columns(tickets)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        report = {
            "status": "invalid_data", "message": f"Ticket dataset could not be loaded or mapped: {type(exc).__name__}: {exc}",
            "missing_files": [], "ticket_rows": None, "classified_count": 0, "rejected_count": 0,
            "classification_accuracy": None, "category_counts": {}, "priority_counts": {}, "team_counts": {}, "pii_mask_counts": {},
        }
        _write_json(report_dir / "ticket_intelligence_report.json", report)
        return report
    gateway = gateway or GuardrailGateway()
    selected_method = method or os.getenv("SHOPSENSE_TICKET_CLASSIFICATION_METHOD", "zero_shot")
    records: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    for _, row in tickets.iterrows():
        result = gateway.process(row[columns["ticket_text"]], method=selected_method)
        record = result.to_dict()
        # Keep only the case ID locally for support case correlation; customer/order
        # identifiers and all raw/sanitized ticket text are excluded from artifacts.
        record["ticket_id"] = row[columns["ticket_id"]] if columns["ticket_id"] else None
        records.append(record)
        logs.append({"ticket_id": record["ticket_id"], "status": result.status, "rejection_reason": result.rejection_reason})
    frame = pd.DataFrame(records)
    output_file = results_dir / "ticket_results.csv"
    frame.to_csv(output_file, index=False)
    _write_json(report_dir / "ticket_processing_log.json", {"records": logs, "raw_ticket_text_logged": False})
    classified = frame.loc[frame["status"].eq("classified")] if not frame.empty else frame
    rejected = frame.loc[frame["status"].eq("rejected")] if not frame.empty else frame
    counts = {column: _counts(classified[column]) for column in ("category", "priority", "team") if column in classified}
    mask_entries = frame.get("pii_mask_counts", [])
    pii_counts = {kind: int(sum(entry.get(kind, 0) for entry in mask_entries if isinstance(entry, dict))) for kind in ("email", "phone", "order_id", "customer_id")}
    report = {
        "status": "complete", "message": "Processed cleaned ticket rows through the guardrail gateway.",
        "missing_files": [], "ticket_rows": int(len(tickets)), "classified_count": int(len(classified)),
        "rejected_count": int(len(rejected)), "other_processing_failures": int(len(frame) - len(classified) - len(rejected)),
        "classification_method": selected_method, "classification_accuracy": None,
        "classification_accuracy_note": "No labeled evaluation dataset was supplied; classification accuracy is not claimed.",
        "rejection_reasons": _counts(rejected["rejection_reason"]) if len(rejected) else {},
        "category_counts": counts.get("category", {}), "priority_counts": counts.get("priority", {}),
        "team_counts": counts.get("team", {}), "pii_mask_counts": pii_counts,
        "token_count_exact_classified": int(classified.get("token_count_exact", pd.Series(dtype="boolean")).astype("boolean").fillna(False).sum()) if len(classified) else 0,
        "ticket_results_file": str(output_file), "raw_ticket_text_saved": False,
    }
    _write_json(report_dir / "ticket_intelligence_report.json", report)
    return report


def _counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.dropna().value_counts().items()}


def _normalize(value: str) -> str:
    source = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    return re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
