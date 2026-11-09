"""Structured classification and guardrail result schemas."""
from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class TicketCategory(str, Enum):
    REFUND = "REFUND"
    LATE_DELIVERY = "LATE_DELIVERY"
    PAYMENT_ISSUE = "PAYMENT_ISSUE"
    MISSING_ITEMS = "MISSING_ITEMS"
    DAMAGED_PRODUCT = "DAMAGED_PRODUCT"
    FRAUD = "FRAUD"
    APP_ISSUE = "APP_ISSUE"
    OTHER = "OTHER"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class SupportTeam(str, Enum):
    PAYMENTS = "Payments"
    DELIVERY = "Delivery"
    REFUNDS = "Refunds"
    PRODUCT_QUALITY = "Product Quality"
    FRAUD_INVESTIGATION = "Fraud Investigation"
    TECHNICAL_SUPPORT = "Technical Support"
    GENERAL_SUPPORT = "General Support"


class ClassificationOutput(BaseModel):
    """Strict JSON schema validated for every model provider response."""
    model_config = ConfigDict(extra="forbid")
    category: TicketCategory
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1, max_length=500)


class SupportAnswerOutput(BaseModel):
    """Strict grounded customer answer; citations are checked by the gateway."""
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1, max_length=3000)
    citations: list[str] = Field(min_length=1, max_length=8)
    requires_human_review: bool
    escalation_reason: str = Field(default="", max_length=500)


class PromptPayload(BaseModel):
    """System and user messages passed only from the secure gateway to a provider."""
    system: str
    user: str
    method: str


def validate_classification_output(output: Any) -> ClassificationOutput:
    """Parse provider JSON and enforce the shared allowed-category schema."""
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("Model output must be valid JSON.") from exc
    if not isinstance(output, dict):
        raise ValueError("Model output must be a JSON object.")
    values = dict(output)
    category = values.get("category")
    if isinstance(category, str):
        values["category"] = category.strip().upper()
    try:
        return ClassificationOutput.model_validate(values)
    except ValidationError as exc:
        raise ValueError("Model output failed the allowed classification schema.") from exc


def validate_support_answer(output: Any) -> SupportAnswerOutput:
    """Parse JSON support output and enforce required customer-safe fields."""
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("Support output must be valid JSON.") from exc
    if not isinstance(output, dict):
        raise ValueError("Support output must be a JSON object.")
    try:
        return SupportAnswerOutput.model_validate(output)
    except ValidationError as exc:
        raise ValueError("Support output failed the required response schema.") from exc
