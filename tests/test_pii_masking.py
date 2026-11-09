from app.guardrails.pii_masking import MaskingPatterns, mask_pii


def test_masks_email_phone_order_and_customer_identifiers():
    raw = "My order ORD123456 for CUST998877 is delayed. Contact alice@example.com at +1 (415) 555-2671."
    result = mask_pii(raw)
    assert result.sanitized_text == "My order [ORDER_ID] for [CUSTOMER_ID] is delayed. Contact [EMAIL] at [PHONE]."
    assert result.counts == {"order_id": 1, "customer_id": 1, "email": 1, "phone": 1}
    for secret in ("ORD123456", "CUST998877", "alice@example.com", "415) 555-2671"):
        assert secret not in result.sanitized_text


def test_masking_patterns_are_configurable():
    custom = MaskingPatterns(order_id=r"\bCASE-\d+\b")
    result = mask_pii("Case CASE-12345 is delayed", custom)
    assert result.sanitized_text == "Case [ORDER_ID] is delayed"
    assert result.counts["order_id"] == 1
