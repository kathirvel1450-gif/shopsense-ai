"""Classification entry points; they can classify only through GuardrailGateway."""
from __future__ import annotations

from typing import Any

from app.guardrails.model_gateway import GuardrailGateway


def classify_zero_shot(ticket_text: Any, gateway: GuardrailGateway | None = None):
    """Run zero-shot classification through validation, masking, and token checks."""
    return (gateway or GuardrailGateway()).process(ticket_text, method="zero_shot")


def classify_few_shot(ticket_text: Any, gateway: GuardrailGateway | None = None):
    """Run few-shot classification through the same mandatory guardrail gateway."""
    return (gateway or GuardrailGateway()).process(ticket_text, method="few_shot")
