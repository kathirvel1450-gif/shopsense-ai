"""The sole application gateway for all classification model calls."""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx
from dotenv import load_dotenv

from app.guardrails.pii_masking import MaskingPatterns, mask_pii
from app.guardrails.prioritization import assign_priority
from app.guardrails.prompt_builder import build_prompt
from app.guardrails.routing import route_ticket
from app.guardrails.schemas import ClassificationOutput, PromptPayload, SupportAnswerOutput, validate_classification_output, validate_support_answer
from app.guardrails.token_counter import TokenCount, count_tokens
from app.guardrails.validators import InputValidation, validate_ticket_input

logger = logging.getLogger(__name__)


class ClassificationProvider(Protocol):
    """Provider protocol used only inside the secure gateway."""
    def complete(self, prompt: PromptPayload) -> Any: ...


@dataclass(frozen=True)
class GatewaySettings:
    max_characters: int = 20000
    max_ticket_tokens: int = 512
    max_prompt_tokens: int = 8192
    model: str = "gpt-4o-mini"

    @classmethod
    def from_environment(cls) -> "GatewaySettings":
        """Load safe numeric caps from environment, falling back on defaults."""
        load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
        return cls(
            max_characters=_env_int("SHOPSENSE_TICKET_MAX_CHARACTERS", 20000),
            max_ticket_tokens=_env_int("SHOPSENSE_TICKET_MAX_TOKENS", 512),
            max_prompt_tokens=_env_int("SHOPSENSE_TICKET_MAX_PROMPT_TOKENS", 8192),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )


@dataclass
class PreparedTicket:
    accepted: bool
    status: str
    rejection_reason: str | None = None
    sanitized_text: str | None = None
    mask_counts: dict[str, int] | None = None
    token_count: int | None = None
    token_method: str | None = None
    token_count_exact: bool | None = None


@dataclass
class GatewayResult:
    accepted: bool
    status: str
    method: str
    rejection_reason: str | None = None
    category: str | None = None
    confidence: float | None = None
    rationale: str | None = None
    priority: str | None = None
    priority_reason: str | None = None
    team: str | None = None
    requires_human_review: bool = False
    routing_reason: str | None = None
    pii_mask_counts: dict[str, int] | None = None
    token_count: int | None = None
    token_method: str | None = None
    token_count_exact: bool | None = None
    prompt_token_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize safe processing metadata; never includes ticket text or IDs."""
        return asdict(self)


@dataclass
class GroundedGatewayResult:
    """Safe model answer metadata; never contains raw input or retrieved text."""
    accepted: bool
    status: str
    answer: str | None = None
    citations: list[str] | None = None
    requires_human_review: bool = False
    escalation_reason: str | None = None
    rejection_reason: str | None = None
    token_count: int | None = None
    token_method: str | None = None
    token_count_exact: bool | None = None
    prompt_token_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GuardrailGateway:
    """Validate → mask → count tokens → build prompt → call provider → validate output."""

    def __init__(
        self,
        provider: ClassificationProvider | None = None,
        settings: GatewaySettings | None = None,
        masking_patterns: MaskingPatterns | None = None,
        token_counter=count_tokens,
    ) -> None:
        self.settings = settings or GatewaySettings.from_environment()
        self.masking_patterns = masking_patterns or MaskingPatterns()
        self._token_counter = token_counter
        self._provider = provider or _configured_provider(self.settings.model)

    @property
    def provider_mode(self) -> str:
        """Return a non-secret provider label suitable for service health status."""
        return "openai_compatible" if isinstance(self._provider, _OpenAICompatibleProvider) else "deterministic_mock"

    def prepare(self, raw_ticket: Any) -> PreparedTicket:
        """Run input validation, PII masking, and token validation without a model call."""
        validation: InputValidation = validate_ticket_input(raw_ticket, self.settings.max_characters)
        if not validation.valid:
            return PreparedTicket(False, "rejected", validation.reason)
        masked = mask_pii(validation.normalized_text or "", self.masking_patterns)
        token_info: TokenCount = self._token_counter(masked.sanitized_text, self.settings.model)
        if getattr(self._provider, "requires_exact_tokenizer", False) and not token_info.exact_for_model:
            logger.warning("Ticket rejected reason=reliable_tokenizer_unavailable")
            return PreparedTicket(False, "rejected", "reliable_tokenizer_unavailable", mask_counts=masked.counts, token_count=token_info.count, token_method=token_info.method, token_count_exact=False)
        if token_info.count > self.settings.max_ticket_tokens:
            logger.warning("Ticket rejected reason=token_limit token_count=%d", token_info.count)
            return PreparedTicket(False, "rejected", "token_limit", mask_counts=masked.counts, token_count=token_info.count, token_method=token_info.method, token_count_exact=token_info.exact_for_model)
        return PreparedTicket(True, "validated", sanitized_text=masked.sanitized_text, mask_counts=masked.counts, token_count=token_info.count, token_method=token_info.method, token_count_exact=token_info.exact_for_model)

    def process(self, raw_ticket: Any, method: str = "zero_shot") -> GatewayResult:
        """Classify only after the complete guardrail preparation sequence passes."""
        if method not in {"zero_shot", "few_shot"}:
            return GatewayResult(False, "rejected", method, rejection_reason="invalid_classification_method")
        prepared = self.prepare(raw_ticket)
        if not prepared.accepted:
            return _from_prepared(prepared, method)
        prompt = build_prompt(prepared.sanitized_text or "", method)
        prompt_count: TokenCount = self._token_counter(f"{prompt.system}\n{prompt.user}", self.settings.model)
        if prompt_count.count > self.settings.max_prompt_tokens:
            logger.warning("Ticket rejected reason=prompt_token_limit token_count=%d", prompt_count.count)
            result = _from_prepared(prepared, method)
            result.accepted, result.status, result.rejection_reason = False, "rejected", "prompt_token_limit"
            result.prompt_token_count = prompt_count.count
            return result
        try:
            raw_output = self._provider.complete(prompt)
        except Exception as exc:
            logger.error("Ticket model provider failed exception_type=%s", type(exc).__name__)
            result = _from_prepared(prepared, method)
            result.status = "provider_error"
            result.rejection_reason = "model_provider_error"
            result.prompt_token_count = prompt_count.count
            return result
        try:
            classification: ClassificationOutput = validate_classification_output(raw_output)
        except ValueError:
            logger.warning("Ticket model output rejected reason=invalid_schema")
            result = _from_prepared(prepared, method)
            result.status = "output_invalid"
            result.rejection_reason = "invalid_model_output"
            result.prompt_token_count = prompt_count.count
            return result
        # Re-mask generated rationale before returning or storing it.
        safe_rationale = mask_pii(classification.rationale, self.masking_patterns).sanitized_text
        priority = assign_priority(classification.category, prepared.sanitized_text or "")
        routing = route_ticket(classification.category, priority["priority"])
        logger.info("Ticket classified category=%s method=%s tokens=%d", classification.category.value, method, prepared.token_count or 0)
        return GatewayResult(
            accepted=True, status="classified", method=method, category=classification.category.value,
            confidence=classification.confidence, rationale=safe_rationale,
            priority=priority["priority"], priority_reason=priority["reason"], team=routing["team"],
            requires_human_review=routing["requires_human_review"], routing_reason=routing["routing_reason"],
            pii_mask_counts=prepared.mask_counts, token_count=prepared.token_count, token_method=prepared.token_method,
            token_count_exact=prepared.token_count_exact, prompt_token_count=prompt_count.count,
        )

    def generate_grounded_response(
        self,
        prepared: PreparedTicket,
        policy_context: list[dict[str, str]],
        system_instructions: str,
        history: list[dict[str, str]] | None = None,
    ) -> GroundedGatewayResult:
        """Generate a support answer from prepared input and masked policy context.

        This method reuses the private provider configured on this gateway. It
        accepts only an already validated/masked PreparedTicket, masks context
        and history again, validates token budget, and strictly validates output.
        """
        if not prepared.accepted or not prepared.sanitized_text:
            return GroundedGatewayResult(False, "rejected", rejection_reason=prepared.rejection_reason or "input_not_prepared")
        safe_context = []
        for item in policy_context:
            ref = mask_pii(str(item.get("source_ref", "policy reference")), self.masking_patterns).sanitized_text
            body = mask_pii(str(item.get("content", "")), self.masking_patterns).sanitized_text
            if body.strip():
                safe_context.append({"source_ref": ref, "content": body})
        if not safe_context:
            return GroundedGatewayResult(False, "insufficient_context", rejection_reason="no_policy_context", token_count=prepared.token_count, token_method=prepared.token_method, token_count_exact=prepared.token_count_exact)
        safe_history = []
        for item in (history or [])[-8:]:
            role = "assistant" if item.get("role") == "assistant" else "user"
            content = mask_pii(str(item.get("content", "")), self.masking_patterns).sanitized_text
            safe_history.append({"role": role, "content": content})
        user_message = json.dumps({"question": prepared.sanitized_text, "policy_context": safe_context, "conversation_history": safe_history}, ensure_ascii=False)
        prompt = PromptPayload(system=system_instructions, user=user_message, method="rag")
        prompt_count: TokenCount = self._token_counter(f"{prompt.system}\n{prompt.user}", self.settings.model)
        if prompt_count.count > self.settings.max_prompt_tokens:
            logger.warning("RAG response rejected reason=prompt_token_limit token_count=%d", prompt_count.count)
            return GroundedGatewayResult(False, "rejected", rejection_reason="prompt_token_limit", token_count=prepared.token_count, token_method=prepared.token_method, token_count_exact=prepared.token_count_exact, prompt_token_count=prompt_count.count)
        try:
            raw_output = self._provider.complete(prompt)
        except Exception as exc:
            logger.error("RAG model provider failed exception_type=%s", type(exc).__name__)
            return GroundedGatewayResult(False, "provider_error", rejection_reason="model_provider_error", token_count=prepared.token_count, token_method=prepared.token_method, token_count_exact=prepared.token_count_exact, prompt_token_count=prompt_count.count)
        try:
            output: SupportAnswerOutput = validate_support_answer(raw_output)
        except ValueError:
            logger.warning("RAG model output rejected reason=invalid_schema")
            return GroundedGatewayResult(False, "output_invalid", rejection_reason="invalid_model_output", token_count=prepared.token_count, token_method=prepared.token_method, token_count_exact=prepared.token_count_exact, prompt_token_count=prompt_count.count)
        allowed_refs = {item["source_ref"] for item in safe_context}
        if not set(output.citations).issubset(allowed_refs):
            logger.warning("RAG model output rejected reason=invalid_citation")
            return GroundedGatewayResult(False, "output_invalid", rejection_reason="invalid_citation", token_count=prepared.token_count, token_method=prepared.token_method, token_count_exact=prepared.token_count_exact, prompt_token_count=prompt_count.count)
        answer = mask_pii(output.answer, self.masking_patterns).sanitized_text
        if _unverified_refund_claim(answer):
            logger.warning("RAG model output rejected reason=unverified_transaction_claim")
            return GroundedGatewayResult(False, "output_invalid", rejection_reason="unverified_transaction_claim", token_count=prepared.token_count, token_method=prepared.token_method, token_count_exact=prepared.token_count_exact, prompt_token_count=prompt_count.count)
        reason = mask_pii(output.escalation_reason, self.masking_patterns).sanitized_text
        return GroundedGatewayResult(True, "answered", answer=answer, citations=output.citations, requires_human_review=output.requires_human_review, escalation_reason=reason or None, token_count=prepared.token_count, token_method=prepared.token_method, token_count_exact=prepared.token_count_exact, prompt_token_count=prompt_count.count)


class _OpenAICompatibleProvider:
    """OpenAI-compatible chat-completions adapter; receives gateway prompt only."""
    requires_exact_tokenizer = True

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self._api_key, self._model = api_key, model
        self._endpoint = base_url.rstrip("/") + "/chat/completions"

    def complete(self, prompt: PromptPayload) -> str:
        response = httpx.post(
            self._endpoint,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            json={"model": self._model, "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": prompt.system}, {"role": "user", "content": prompt.user}]},
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Provider response content was not text.")
        return content


class _DeterministicMockProvider:
    """Local deterministic category fallback for development and tests."""
    def complete(self, prompt: PromptPayload) -> dict[str, Any]:
        """Classify only the masked ticket text using transparent keyword rules."""
        body = json.loads(prompt.user)
        if prompt.method == "rag":
            context = body.get("policy_context", [])
            first = context[0] if context else {}
            ref = first.get("source_ref", "synthetic demonstration policy")
            excerpt = " ".join(first.get("content", "").split())[:360]
            if not excerpt:
                return {"answer": "I could not find enough policy information to answer. A human support agent should review this request.", "citations": [ref], "requires_human_review": True, "escalation_reason": "No usable policy excerpt was retrieved."}
            sensitive = bool(re.search(r"fraud|unauthori[sz]ed|payment|refund|injur|allerg|account", body.get("question", ""), re.I))
            return {"answer": f"This is a synthetic demonstration policy, not actual retailer terms. According to {ref}: {excerpt}", "citations": [ref], "requires_human_review": sensitive, "escalation_reason": "Sensitive or transaction-specific questions need human review." if sensitive else ""}
        text = body.get("ticket_text", "").casefold()
        rules = [
            ("FRAUD", ("fraud", "unauthorized", "unauthorised", "scam", "stolen")),
            ("DAMAGED_PRODUCT", ("damaged", "broken", "spoiled", "leaking")),
            ("MISSING_ITEMS", ("missing item", "missing items", "not included", "absent")),
            ("REFUND", ("refund", "return", "money back", "reimburse")),
            ("PAYMENT_ISSUE", ("payment", "charged", "charge", "billing", "transaction", "card")),
            ("LATE_DELIVERY", ("late", "delayed", "delivery", "tracking")),
            ("APP_ISSUE", ("app", "crash", "login", "technical", "error")),
        ]
        category = next((name for name, keywords in rules if any(word in text for word in keywords)), "OTHER")
        return {"category": category, "confidence": 0.5, "rationale": "Deterministic local mock classification; not an accuracy estimate."}


def _configured_provider(model: str) -> ClassificationProvider:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return _OpenAICompatibleProvider(api_key, model, os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    return _DeterministicMockProvider()


def _from_prepared(prepared: PreparedTicket, method: str) -> GatewayResult:
    return GatewayResult(
        accepted=prepared.accepted, status=prepared.status, method=method,
        rejection_reason=prepared.rejection_reason, pii_mask_counts=prepared.mask_counts,
        token_count=prepared.token_count, token_method=prepared.token_method,
        token_count_exact=prepared.token_count_exact,
    )


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def _unverified_refund_claim(text: str) -> bool:
    """Detect common unsupported eligibility/transaction promises conservatively."""
    patterns = (
        r"\b(?:your\s+)?refund\s+(?:has been|was|is now)\s+(?:processed|issued|completed|approved)\b",
        r"\bwe\s+(?:have|will)\s+(?:process|issue|approve|send)\s+(?:your\s+)?refund\b",
        r"\byou are\s+(?:eligible|approved|qualified)\s+for\s+(?:a\s+)?refund\b",
    )
    return any(re.search(pattern, text, re.I) for pattern in patterns)
