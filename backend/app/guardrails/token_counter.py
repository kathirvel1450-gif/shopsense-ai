"""Model-aware token counting with an explicitly marked safe estimate fallback."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TokenCount:
    count: int
    method: str
    exact_for_model: bool


def count_tokens(text: str, model: str = "gpt-4o-mini", encoder: Any = None) -> TokenCount:
    """Count tokens with tiktoken when possible; otherwise estimate word pieces.

    The fallback is an estimate, not a character-count proxy and not advertised
    as exact. Production configurations should install tiktoken or pass the
    provider's own tokenizer.
    """
    if encoder is not None:
        return TokenCount(len(encoder.encode(text)), "injected_model_encoder", True)
    try:
        import tiktoken  # type: ignore[import-not-found]

        try:
            model_encoder = tiktoken.encoding_for_model(model)
        except KeyError:
            model_encoder = tiktoken.get_encoding("cl100k_base")
        return TokenCount(len(model_encoder.encode(text, disallowed_special=())), f"tiktoken:{model_encoder.name}", True)
    except ImportError:
        pieces = re.findall(r"[\w]+|[^\w\s]", text, flags=re.UNICODE)
        estimate = sum(max(1, math.ceil(len(piece) / 4)) if piece[0].isalnum() or piece[0] == "_" else 1 for piece in pieces)
        return TokenCount(estimate, "word_piece_estimate", False)
