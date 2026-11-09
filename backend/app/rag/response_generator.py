"""Generate policy-grounded customer answers only through GuardrailGateway."""
from __future__ import annotations

from typing import Any

from app.guardrails.model_gateway import GroundedGatewayResult, GuardrailGateway, PreparedTicket
from app.rag.prompts import build_rag_system_prompt


class RAGResponseGenerator:
    """Call the centralized gateway and provide a safe fallback on model errors."""
    def __init__(self, gateway: GuardrailGateway) -> None:
        self.gateway = gateway

    def generate(
        self,
        prepared: PreparedTicket,
        retrieved: list[dict[str, Any]],
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Generate answer with citations; raw question is never accepted here."""
        if not retrieved:
            return _safe_fallback("No relevant policy text was found. A human support agent should review this request.", [], "policy_context_insufficient")
        gateway_result: GroundedGatewayResult = self.gateway.generate_grounded_response(
            prepared,
            [{"source_ref": item["source_ref"], "content": item["content"]} for item in retrieved],
            build_rag_system_prompt(),
            history,
        )
        if not gateway_result.accepted or gateway_result.status != "answered":
            return _safe_fallback(
                "I could not safely generate an answer from the available policy text. A human support agent should review this request.",
                [item["source_ref"] for item in retrieved],
                gateway_result.rejection_reason or gateway_result.status,
            )
        return {
            "answer": gateway_result.answer,
            "citations": gateway_result.citations or [],
            "requires_human_review": gateway_result.requires_human_review,
            "escalation_reason": gateway_result.escalation_reason,
            "generation_status": gateway_result.status,
        }


def _safe_fallback(answer: str, citations: list[str], reason: str) -> dict[str, Any]:
    return {"answer": answer, "citations": citations, "requires_human_review": True, "escalation_reason": reason, "generation_status": "safe_fallback"}
