"""Fail-closed ticket input validation; logs reasons but never content."""
from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InputValidation:
    valid: bool
    reason: str | None
    normalized_text: str | None
    character_count: int | None


def validate_ticket_input(ticket_text: Any, max_characters: int = 20000) -> InputValidation:
    """Validate presence, type, control characters, whitespace, and raw size."""
    if ticket_text is None:
        return _reject("missing_input")
    if not isinstance(ticket_text, str):
        return _reject("malformed_input")
    if not ticket_text.strip():
        return _reject("empty_or_whitespace")
    if len(ticket_text) > max_characters:
        return _reject("oversized_char_input")
    if any(unicodedata.category(char) in {"Cc", "Cs"} and char not in "\n\r\t" for char in ticket_text):
        return _reject("malformed_control_character")
    return InputValidation(True, None, ticket_text.strip(), len(ticket_text))


def _reject(reason: str) -> InputValidation:
    logger.warning("Ticket rejected reason=%s", reason)
    return InputValidation(False, reason, None, None)
