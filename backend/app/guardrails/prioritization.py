"""Transparent urgency rules for retail support tickets."""
from __future__ import annotations

import re
from typing import Any

from app.guardrails.schemas import TicketCategory, TicketPriority

SAFETY_RE = re.compile(r"\b(unsafe|injur|allerg|contaminat|poison|sick|illness|hurt)\w*\b", re.I)
UNAUTHORIZED_RE = re.compile(r"\b(unauthori[sz]ed|fraud|stolen|account takeover|scam)\b", re.I)


def assign_priority(category: TicketCategory | str, sanitized_text: str = "") -> dict[str, Any]:
    """Assign priority from category and explicit safety/security language."""
    category = TicketCategory(str(category.value if isinstance(category, TicketCategory) else category).upper())
    if SAFETY_RE.search(sanitized_text):
        return {"priority": TicketPriority.URGENT.value, "reason": "Potential product safety or injury language requires immediate human review."}
    if category == TicketCategory.FRAUD:
        return {"priority": TicketPriority.URGENT.value, "reason": "Suspected fraud or unauthorized activity requires immediate investigation."}
    if category == TicketCategory.PAYMENT_ISSUE:
        if UNAUTHORIZED_RE.search(sanitized_text):
            return {"priority": TicketPriority.URGENT.value, "reason": "Payment concern includes unauthorized-activity language."}
        return {"priority": TicketPriority.HIGH.value, "reason": "Payment and billing issues can affect customer funds and are prioritized for review."}
    if category in {TicketCategory.REFUND, TicketCategory.LATE_DELIVERY, TicketCategory.MISSING_ITEMS, TicketCategory.DAMAGED_PRODUCT}:
        return {"priority": TicketPriority.MEDIUM.value, "reason": "Standard order, refund, or product concern; no urgent risk signal detected."}
    if category == TicketCategory.APP_ISSUE:
        return {"priority": TicketPriority.LOW.value, "reason": "Routine app or technical support issue; no urgent risk signal detected."}
    return {"priority": TicketPriority.LOW.value, "reason": "No high-impact category or urgent risk signal detected."}
