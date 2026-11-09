"""Human escalation rules and minimal persistent case records."""
from __future__ import annotations

import re
from typing import Any

from app.rag.conversation import ConversationStore

RISK_RULES = (
    ("fraud_or_account_security", re.compile(r"\b(fraud|unauthori[sz]ed|account takeover|stolen|scam|hacked)\b", re.I)),
    ("payment_status_unverified", re.compile(r"\b(payment|charged|charge|transaction|card)\b", re.I)),
    ("refund_eligibility_unverified", re.compile(r"\b(refund|reimburse|eligible for|money back)\b", re.I)),
    ("product_safety_concern", re.compile(r"\b(injur|allerg|contaminat|unsafe|poison|illness|hurt)\w*\b", re.I)),
)


def escalation_reason(question: str, retrieved: list[dict[str, Any]], model_requested_review: bool = False) -> str | None:
    """Return the first transparent escalation reason, or None when routine."""
    for reason, pattern in RISK_RULES:
        if pattern.search(question):
            return reason
    if not retrieved:
        return "policy_context_insufficient"
    if model_requested_review:
        return "model_uncertainty"
    return None


class EscalationManager:
    """Create human-review cases without storing original customer text."""
    def __init__(self, store: ConversationStore) -> None:
        self.store = store

    def create(self, conversation_id: str, reason_code: str, masked_summary: str = "") -> dict[str, Any]:
        safe_reason = re.sub(r"[^a-z0-9_-]", "_", reason_code.casefold())[:64] or "human_review"
        case_id = self.store.record_escalation(conversation_id, safe_reason, masked_summary)
        return {"escalation_id": case_id, "status": "HUMAN_REVIEW", "reason_code": safe_reason, "message": "This request has been referred for human review. No transaction action has been performed."}
