"""Configurable PII detection and irreversible masking for model-bound text."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Pattern


@dataclass(frozen=True)
class MaskingPatterns:
    email: str = r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
    order_id: str = r"(?i)(?P<label>\border(?:\s+id)?\s*[:#-]?\s*)(?P<order_id>(?:ORD[-#:]?\d{4,}|\d{5,}))\b|\b(?P<order_code>ORD[-#:]?\d{4,})\b"
    customer_id: str = r"(?i)\b(?:CUST(?:OMER)?[-#:]?[A-Z0-9]{3,}|CUSTOMER\s+ID\s*[:#-]?\s*[A-Z0-9-]{3,})\b"
    phone: str = r"(?<![A-Za-z0-9])(?:\+?\d{1,3}[\s().-]*)?(?:\(?\d{3,4}\)?[\s().-]*)?\d{3}[\s.-]?\d{4}(?!\d)"


@dataclass(frozen=True)
class MaskingResult:
    sanitized_text: str
    counts: dict[str, int]


def mask_pii(text: str, patterns: MaskingPatterns | None = None) -> MaskingResult:
    """Mask order/customer IDs before generic phone patterns to prevent partial leaks."""
    if not isinstance(text, str):
        raise TypeError("PII masking accepts sanitized string input only.")
    patterns = patterns or MaskingPatterns()
    rules: list[tuple[str, Pattern[str], str]] = [
        ("order_id", re.compile(patterns.order_id), "[ORDER_ID]"),
        ("customer_id", re.compile(patterns.customer_id), "[CUSTOMER_ID]"),
        ("email", re.compile(patterns.email), "[EMAIL]"),
        ("phone", re.compile(patterns.phone), "[PHONE]"),
    ]
    sanitized = text
    counts: dict[str, int] = {}
    for name, pattern, replacement in rules:
        if name == "order_id" and "label" in pattern.groupindex:
            sanitized, count = pattern.subn(lambda match: f"{match.group('label')}{replacement}", sanitized)
        else:
            sanitized, count = pattern.subn(replacement, sanitized)
        counts[name] = count
    return MaskingResult(sanitized, counts)
