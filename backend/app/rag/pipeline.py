"""Guarded RAG support pipeline and conversation orchestration."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.data_engine.pipeline import configured_paths, project_root
from app.guardrails.model_gateway import GuardrailGateway, PreparedTicket
from app.guardrails.pii_masking import mask_pii
from app.rag.conversation import ConversationStore
from app.rag.escalation import EscalationManager, escalation_reason
from app.rag.prompts import build_rag_system_prompt
from app.rag.response_generator import RAGResponseGenerator
from app.rag.retrieval import PolicyRetriever


class RAGAssistant:
    """Coordinate input guardrails, retrieval, guarded generation, and memory."""
    def __init__(
        self,
        retriever: PolicyRetriever | None = None,
        gateway: GuardrailGateway | None = None,
        conversation_store: ConversationStore | None = None,
    ) -> None:
        load_dotenv(project_root() / ".env", override=False)
        paths = configured_paths()
        self.retriever = retriever or PolicyRetriever()
        database_path = Path(os.getenv("RAG_CONVERSATION_DB", paths["outputs"] / "assistant" / "conversations.sqlite3"))
        if not database_path.is_absolute():
            database_path = project_root() / database_path
        self.conversations = conversation_store or ConversationStore(database_path)
        self.gateway = gateway or GuardrailGateway()
        self.response_generator = RAGResponseGenerator(self.gateway)
        self.escalations = EscalationManager(self.conversations)

    def health(self) -> dict[str, Any]:
        """Return configuration/index status without calling embeddings or an LLM."""
        status = self.retriever.status()
        return {"status": "ok" if status["document_count"] else "missing_policy_documents", "policy_documents": status["document_count"], "chunks": status["chunk_count"], "indexed_chunks": status["indexed_chunk_count"], "embedding_provider": status["embedding_provider"], "embedding_semantic": status["embedding_semantic"], "vector_backend": status["vector_backend"], "retrieval_mode": status["retrieval_mode"], "llm_mode": self.gateway.provider_mode, "synthetic_policies": status["synthetic_policies"]}

    def retrieve(self, question: Any, top_k: int | None = None) -> dict[str, Any]:
        """Validate/mask/token-check the query before performing similarity search."""
        prepared = self.gateway.prepare(question)
        if not prepared.accepted:
            return {"status": "rejected", "rejection_reason": prepared.rejection_reason, "documents": [], "pii_mask_counts": prepared.mask_counts}
        docs = self.retriever.retrieve(prepared.sanitized_text or "", top_k=top_k)
        return {
            "status": "retrieved" if docs else "insufficient_context", "documents": [_citation(doc) for doc in docs],
            "retrieved_count": len(docs), "pii_mask_counts": prepared.mask_counts,
            "retrieval_mode": self.retriever.status()["retrieval_mode"],
        }

    def chat(self, question: Any, conversation_id: str | None = None) -> dict[str, Any]:
        """Answer with retrieved policies; persist only masked conversation text."""
        prepared: PreparedTicket = self.gateway.prepare(question)
        if not prepared.accepted:
            return {"status": "rejected", "rejection_reason": prepared.rejection_reason, "answer": None, "conversation_id": None, "citations": [], "requires_human_review": False, "refund_status": "NOT_CHECKED", "transaction_action": "NONE"}
        try:
            session_id = self.conversations.create_conversation_id(conversation_id)
        except ValueError:
            return {"status": "rejected", "rejection_reason": "invalid_conversation_id", "answer": None, "conversation_id": None, "citations": [], "requires_human_review": False, "refund_status": "NOT_CHECKED", "transaction_action": "NONE"}
        history = self.conversations.history(session_id)
        sanitized_question = prepared.sanitized_text or ""
        retrieved = self.retriever.retrieve(sanitized_question)
        citations = [_citation(doc) for doc in retrieved]
        trigger = escalation_reason(sanitized_question, retrieved)
        if trigger == "policy_context_insufficient":
            answer = "I couldn't find enough applicable synthetic policy text to answer confidently. A human support agent should review this request. No transaction action has been performed."
            generated = {"answer": answer, "citations": [], "requires_human_review": True, "escalation_reason": trigger, "generation_status": "insufficient_context"}
        elif trigger:
            generated = self._sensitive_safe_response(trigger, citations)
        else:
            generated = self.response_generator.generate(prepared, retrieved, history)
            if generated["requires_human_review"]:
                trigger = escalation_reason(sanitized_question, retrieved, model_requested_review=True)
        answer = mask_pii(generated["answer"], self.gateway.masking_patterns).sanitized_text
        citations_out = generated.get("citations", [])
        if not citations_out and retrieved and generated["generation_status"] != "insufficient_context":
            citations_out = [doc["source_ref"] for doc in retrieved[:2]]
        escalation = self.escalations.create(session_id, trigger, sanitized_question) if trigger else None
        self.conversations.save_turn(session_id, sanitized_question, answer)
        status = "escalated" if escalation else "answered"
        return {
            "status": status, "conversation_id": session_id, "answer": answer,
            "citations": citations_out, "requires_human_review": bool(escalation or generated["requires_human_review"]),
            "escalation": escalation, "retrieved_count": len(retrieved),
            "synthetic_policy_content": bool(retrieved) and all(doc["synthetic_policy"] for doc in retrieved),
            "refund_status": "NOT_CHECKED", "transaction_action": "NONE",
        }

    def prepare_question(self, question: Any) -> PreparedTicket:
        """Expose the gateway's safe pre-retrieval stage to other RAG components."""
        return self.gateway.prepare(question)

    def _sensitive_safe_response(self, reason: str, citations: list[dict[str, Any]]) -> dict[str, Any]:
        refs = [item["source_ref"] for item in citations[:3]]
        if reason == "fraud_or_account_security":
            answer = "This may involve sensitive account or payment security. Do not share passwords, full card details, or one-time codes here. Use the retailer's official secure support channel for urgent review. I cannot verify or change account/payment status, and no action has been performed."
        elif reason == "payment_status_unverified":
            answer = "I cannot verify a payment, charge, or settlement in this demonstration. Please use the official payment support channel for a transaction review. No payment or refund action has been performed."
        elif reason == "refund_eligibility_unverified":
            answer = "The synthetic demonstration policy does not establish refund eligibility. An authorized agent must review actual order records and retailer terms. No refund has been approved or processed."
        else:
            answer = "This concern needs human review. I cannot verify product safety or an order in this demonstration. No transaction action has been performed."
        return {"answer": answer, "citations": refs, "requires_human_review": True, "escalation_reason": reason, "generation_status": "safe_sensitive_fallback"}


def _citation(doc: dict[str, Any]) -> dict[str, Any]:
    return {"source_name": doc["source_name"], "source_ref": doc["source_ref"], "section": doc["section"], "similarity": doc["similarity"], "synthetic_policy": doc["synthetic_policy"]}
