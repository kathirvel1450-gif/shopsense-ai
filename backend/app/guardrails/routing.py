"""Ticket routing and mandatory human-review recommendations."""
from __future__ import annotations

from typing import Any

from app.guardrails.schemas import SupportTeam, TicketCategory

TEAM_BY_CATEGORY = {
    TicketCategory.REFUND: SupportTeam.REFUNDS,
    TicketCategory.LATE_DELIVERY: SupportTeam.DELIVERY,
    TicketCategory.PAYMENT_ISSUE: SupportTeam.PAYMENTS,
    TicketCategory.MISSING_ITEMS: SupportTeam.DELIVERY,
    TicketCategory.DAMAGED_PRODUCT: SupportTeam.PRODUCT_QUALITY,
    TicketCategory.FRAUD: SupportTeam.FRAUD_INVESTIGATION,
    TicketCategory.APP_ISSUE: SupportTeam.TECHNICAL_SUPPORT,
    TicketCategory.OTHER: SupportTeam.GENERAL_SUPPORT,
}


def route_ticket(category: TicketCategory | str, priority: str) -> dict[str, Any]:
    """Recommend a support team and human review for fraud/payment risks."""
    parsed = TicketCategory(str(category.value if isinstance(category, TicketCategory) else category).upper())
    team = TEAM_BY_CATEGORY[parsed]
    requires_review = parsed == TicketCategory.FRAUD or (parsed == TicketCategory.PAYMENT_ISSUE and priority in {"HIGH", "URGENT"})
    reason = "Human review required for suspected fraud or high-risk payment concerns." if requires_review else f"Route to {team.value} based on the classified ticket category."
    return {"team": team.value, "requires_human_review": requires_review, "routing_reason": reason}
