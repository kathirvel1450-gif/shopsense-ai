"""Customer support assistant API; all free text is processed through guardrails."""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.rag.pipeline import RAGAssistant
from app.rag.refund_agent import RefundAgent

router = APIRouter(prefix="/assistant", tags=["policy-grounded assistant"])


class AssistantRequest(BaseModel):
    question: Any = None
    conversation_id: str | None = None


class EscalationRequest(BaseModel):
    conversation_id: str | None = None
    reason: str = "customer_requested"
    summary: Any = None


@router.post("/chat")
def chat(request: AssistantRequest) -> dict[str, Any]:
    """Answer from synthetic policy context; response excludes retrieved text."""
    return RAGAssistant().chat(request.question, request.conversation_id)


@router.post("/retrieve")
def retrieve(request: AssistantRequest) -> dict[str, Any]:
    """Return safe source metadata only, never policy chunk contents."""
    return RAGAssistant().retrieve(request.question)


@router.post("/refund")
def refund(request: AssistantRequest) -> dict[str, Any]:
    """Start a simulated review workflow; this route cannot execute refunds."""
    assistant = RAGAssistant()
    return RefundAgent(assistant).request(request.question, request.conversation_id)


@router.post("/escalate")
def escalate(request: EscalationRequest) -> dict[str, Any]:
    """Record a minimal masked escalation summary for a valid conversation."""
    assistant = RAGAssistant()
    prepared = assistant.prepare_question(request.summary)
    if not prepared.accepted:
        return {"status": "rejected", "reason": prepared.rejection_reason, "created": False}
    try:
        session_id = assistant.conversations.create_conversation_id(request.conversation_id)
    except ValueError:
        return {"status": "rejected", "reason": "invalid_conversation_id", "created": False}
    case = assistant.escalations.create(session_id, "customer_requested", prepared.sanitized_text or "")
    return {"status": "escalated", "created": True, "case": case}


@router.get("/health")
def health() -> dict[str, Any]:
    """Return policy/index/provider mode without exposing local paths or secrets."""
    return RAGAssistant().health()
