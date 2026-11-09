from app.guardrails.token_counter import TokenCount, count_tokens


class FixedEncoder:
    def encode(self, text):
        return text.split()


def test_token_count_uses_injected_model_tokenizer_exactly():
    result = count_tokens("one two three", encoder=FixedEncoder())
    assert result == TokenCount(3, "injected_model_encoder", True)


def test_fallback_is_explicitly_an_estimate_not_character_count():
    result = count_tokens("Hello, world!")
    assert result.count > 0
    assert result.method in {"word_piece_estimate"} or result.method.startswith("tiktoken:")
    if result.method == "word_piece_estimate":
        assert result.exact_for_model is False
        assert result.count != len("Hello, world!")
