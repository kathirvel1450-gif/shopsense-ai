import logging

import pytest

from app.guardrails.validators import validate_ticket_input


@pytest.mark.parametrize("value,reason", [(None, "missing_input"), ("", "empty_or_whitespace"), (" \n\t ", "empty_or_whitespace"), (123, "malformed_input"), ("bad\x00text", "malformed_control_character")])
def test_invalid_ticket_inputs_are_rejected_without_logging_content(caplog, value, reason):
    caplog.set_level(logging.WARNING)
    result = validate_ticket_input(value)
    assert result.valid is False
    assert result.reason == reason
    assert "bad" not in caplog.text


def test_raw_character_limit_is_separate_from_token_count():
    assert validate_ticket_input("x" * 6, max_characters=5).reason == "oversized_char_input"
    result = validate_ticket_input("hello", max_characters=5)
    assert result.valid is True
    assert result.character_count == 5
