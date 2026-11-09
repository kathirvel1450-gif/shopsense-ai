import logging

from app.guardrails.model_gateway import GatewaySettings, GuardrailGateway
from app.guardrails.token_counter import TokenCount


class WordCounter:
    def __call__(self, text, model):
        return TokenCount(len(text.split()), "test_word_counter", True)


class SpyProvider:
    def __init__(self, output=None):
        self.output = output or {"category": "LATE_DELIVERY", "confidence": 0.8, "rationale": "Delivery is delayed."}
        self.prompts = []

    def complete(self, prompt):
        self.prompts.append(prompt)
        return self.output


def test_gateway_masks_all_pii_before_provider_and_response(caplog):
    raw = "Order ORD123456 for CUST998877 delayed. Email alice@example.com or call +1 (415) 555-2671."
    provider = SpyProvider({"category": "LATE_DELIVERY", "confidence": 0.8, "rationale": "We found alice@example.com on order ORD123456."})
    gateway = GuardrailGateway(provider, GatewaySettings(1000, 100, 1000), token_counter=WordCounter())
    caplog.set_level(logging.DEBUG)

    result = gateway.process(raw, "zero_shot")

    assert result.status == "classified"
    assert len(provider.prompts) == 1
    payload = provider.prompts[0].system + provider.prompts[0].user
    for secret in ("ORD123456", "CUST998877", "alice@example.com", "415) 555-2671"):
        assert secret not in payload
        assert secret not in caplog.text
    assert "[ORDER_ID]" in payload and "[EMAIL]" in payload and "[PHONE]" in payload
    assert "alice@example.com" not in (result.rationale or "")
    assert "raw_ticket" not in result.to_dict()


def test_rejected_input_and_token_limit_never_reach_model():
    provider = SpyProvider()
    gateway = GuardrailGateway(provider, GatewaySettings(100, 3, 1000), token_counter=WordCounter())
    assert gateway.process("   ").status == "rejected"
    too_long = gateway.process("one two three four")
    assert too_long.rejection_reason == "token_limit"
    assert provider.prompts == []
    exact = gateway.process("one two")
    assert exact.status == "classified"
    assert len(provider.prompts) == 1


def test_model_output_schema_failure_is_rejected_without_echoing_output():
    provider = SpyProvider({"category": "NOT_ALLOWED", "confidence": 0.8, "rationale": "untrusted response content"})
    result = GuardrailGateway(provider, GatewaySettings(100, 100, 1000), token_counter=WordCounter()).process("A standard question")
    assert result.status == "output_invalid"
    assert result.category is None
    assert "untrusted response content" not in str(result.to_dict())


def test_external_provider_fails_closed_without_reliable_tokenizer():
    from app.guardrails.token_counter import TokenCount

    class ExternalProvider(SpyProvider):
        requires_exact_tokenizer = True

    provider = ExternalProvider()
    approximate_counter = lambda text, model: TokenCount(1, "estimate", False)
    result = GuardrailGateway(provider, GatewaySettings(100, 100, 1000), token_counter=approximate_counter).process("hello")
    assert result.status == "rejected"
    assert result.rejection_reason == "reliable_tokenizer_unavailable"
    assert provider.prompts == []


def test_provider_errors_are_not_logged_or_returned_with_sensitive_details(caplog):
    class BrokenProvider:
        def complete(self, prompt):
            raise RuntimeError("alice@example.com ORD123456")

    result = GuardrailGateway(BrokenProvider(), GatewaySettings(100, 100, 1000), token_counter=WordCounter()).process("hello")
    assert result.status == "provider_error"
    assert "alice@example.com" not in caplog.text
    assert "ORD123456" not in str(result.to_dict())
