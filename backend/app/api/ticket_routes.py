"""Guarded single-ticket and batch-processing API endpoints."""
import json
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.data_engine.pipeline import configured_paths
from app.guardrails.model_gateway import GuardrailGateway
from app.guardrails.pipeline import run_ticket_pipeline

router = APIRouter(prefix="/tickets", tags=["ticket intelligence"])


class TicketRequest(BaseModel):
    """Ticket body accepted for guardrailed processing; no ID fields are returned."""
    ticket_text: Any = None
    method: Literal["zero_shot", "few_shot"] = "zero_shot"


@router.post("/validate")
def validate_ticket(request: TicketRequest | None = None) -> dict[str, Any]:
    """Validate, mask, and token-check without making a model call."""
    gateway = GuardrailGateway()
    prepared = gateway.prepare(request.ticket_text if request else None)
    return {
        "valid": prepared.accepted, "status": prepared.status, "rejection_reason": prepared.rejection_reason,
        "pii_mask_counts": prepared.mask_counts, "token_count": prepared.token_count,
        "token_method": prepared.token_method, "token_count_exact": prepared.token_count_exact,
        "model_called": False,
    }


@router.post("/classify")
def classify_ticket(request: TicketRequest | None = None) -> dict[str, Any]:
    """Classify a single ticket through the mandatory secure model gateway."""
    request = request or TicketRequest()
    return GuardrailGateway().process(request.ticket_text, request.method).to_dict()


@router.post("/process")
def process_ticket(request: TicketRequest | None = None) -> dict[str, Any]:
    """Process one body ticket, or the cleaned ticket CSV when called without a body."""
    if request is not None:
        return GuardrailGateway().process(request.ticket_text, request.method).to_dict()
    return run_ticket_pipeline()


@router.get("/summary")
def ticket_summary() -> dict[str, Any]:
    """Return previously generated aggregate counts; this endpoint never calls a model."""
    paths = configured_paths()
    report_path = paths["outputs"] / "reports" / "ticket_intelligence_report.json"
    if not report_path.is_file():
        ticket_file_exists = (paths["processed"] / "tickets.csv").is_file()
        return {"status": "not_processed" if ticket_file_exists else "missing_inputs", "ticket_file_available": ticket_file_exists, "ticket_rows": None, "classified_count": 0, "rejected_count": 0, "category_counts": {}, "priority_counts": {}, "team_counts": {}, "pii_mask_counts": {}}
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "report_unavailable", "ticket_rows": None, "classified_count": 0, "rejected_count": 0}
    return {key: report.get(key) for key in (
        "status", "message", "missing_files", "ticket_rows", "classified_count", "rejected_count",
        "other_processing_failures", "classification_method", "category_counts", "priority_counts",
        "team_counts", "pii_mask_counts", "rejection_reasons", "classification_accuracy",
        "classification_accuracy_note", "raw_ticket_text_saved",
    )}
