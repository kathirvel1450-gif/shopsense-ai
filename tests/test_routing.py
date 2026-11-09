from app.guardrails.routing import route_ticket


def test_category_routing_and_required_human_review():
    assert route_ticket("REFUND", "MEDIUM")["team"] == "Refunds"
    fraud = route_ticket("FRAUD", "URGENT")
    assert fraud["team"] == "Fraud Investigation"
    assert fraud["requires_human_review"] is True
    payment = route_ticket("PAYMENT_ISSUE", "HIGH")
    assert payment["team"] == "Payments"
    assert payment["requires_human_review"] is True
    assert route_ticket("APP_ISSUE", "LOW")["team"] == "Technical Support"
