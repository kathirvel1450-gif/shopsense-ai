from app.guardrails.prioritization import assign_priority


def test_priority_rules_cover_urgent_payment_safety_and_routine_cases():
    assert assign_priority("FRAUD")["priority"] == "URGENT"
    assert assign_priority("PAYMENT_ISSUE", "Unauthorized transaction")["priority"] == "URGENT"
    assert assign_priority("DAMAGED_PRODUCT", "Product caused an allergic reaction")["priority"] == "URGENT"
    assert assign_priority("PAYMENT_ISSUE")["priority"] == "HIGH"
    assert assign_priority("REFUND")["priority"] == "MEDIUM"
    assert assign_priority("OTHER")["priority"] == "LOW"
