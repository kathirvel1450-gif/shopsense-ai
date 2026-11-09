"""Policy-grounded simulated refund workflow with no real transaction API."""
from __future__ import annotations

from typing import Any

from app.rag.pipeline import RAGAssistant

REFUND_STATES = (
    "REQUEST_RECEIVED", "POLICY_CHECKED", "ELIGIBILITY_REVIEW", "APPROVAL_REQUIRED",
    "HUMAN_REVIEW", "SIMULATED_REFUND_APPROVED", "SIMULATED_REFUND_REJECTED",
)


class RefundAgent:
    """Create a review-only simulation; eligibility and payment are never automated."""
    def __init__(self, assistant: RAGAssistant) -> None:
        self.assistant = assistant

    def request(self, question: Any, conversation_id: str | None = None) -> dict[str, Any]:
        """Retrieve policy guidance and stop at human review without live order access."""
        chat = self.assistant.chat(question, conversation_id)
        if chat["status"] == "rejected":
            return {"status": "rejected", "rejection_reason": chat["rejection_reason"], "refund_state": None, "refund_executed": False, "simulated_only": True}
        states = ["REQUEST_RECEIVED"]
        has_refund_policy = any("refund_policy.md" in str(item) for item in chat.get("citations", []))
        if has_refund_policy:
            states.append("POLICY_CHECKED")
            states.append("ELIGIBILITY_REVIEW")
            states.append("APPROVAL_REQUIRED")
        states.append("HUMAN_REVIEW")
        reason = "No authorized order/payment integration exists, so eligibility cannot be verified; a human must review actual order facts and terms."
        request_id = self.assistant.conversations.record_refund(
            chat["conversation_id"],
            "Refund assistance requested; original text is not retained.",
            "HUMAN_REVIEW", reason, states,
        )
        return {
            "status": "human_review_required", "request_id": request_id,
            "conversation_id": chat["conversation_id"], "refund_state": "HUMAN_REVIEW",
            "state_history": states, "reason": reason, "policy_guidance": chat["answer"],
            "citations": chat["citations"], "requires_human_review": True,
            "refund_executed": False, "simulated_only": True,
            "message": "No real refund was approved or processed.",
        }

    def apply_demo_human_decision(self, request_id: str, approved: bool, reviewer_reference: str) -> dict[str, Any]:
        """Record a local test/demo decision; never calls a payment/refund provider."""
        result = self.assistant.conversations.apply_simulated_refund_decision(request_id, approved, reviewer_reference)
        result["message"] = "This is a simulated review result only; no real refund was executed."
        result["refund_executed"] = False
        return result
