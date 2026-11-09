from pathlib import Path

from app.main import app
from app.rag.conversation import ConversationStore
from app.rag.embeddings import EmbeddingService, LocalHashEmbeddings
from app.rag.pipeline import RAGAssistant
from app.rag.retrieval import PolicyRetriever


def test_guardrail_masks_question_before_storage_or_answer(tmp_path: Path) -> None:
    policies = tmp_path / "policies"
    policies.mkdir()
    (policies / "demo.md").write_text("# Synthetic Demonstration Policy\n\n## Support\n\nContact support for order review.", encoding="utf-8")
    retriever = PolicyRetriever(policy_dir=policies, persist_directory=tmp_path / "index", embeddings=EmbeddingService(LocalHashEmbeddings(64)))
    store = ConversationStore(tmp_path / "conversation.sqlite3")
    assistant = RAGAssistant(retriever=retriever, conversation_store=store)
    result = assistant.chat("Contact a@example.com about order ORD123456")
    assert result["status"] == "answered"
    assert "a@example.com" not in result["answer"]
    assert "ORD123456" not in result["answer"]
    history = store.history(result["conversation_id"])
    assert "a@example.com" not in history[0]["content"]
    assert "ORD123456" not in history[0]["content"]


def test_missing_context_does_not_call_provider(tmp_path: Path) -> None:
    assistant = RAGAssistant(retriever=PolicyRetriever(policy_dir=tmp_path / "missing", persist_directory=tmp_path / "index"), conversation_store=ConversationStore(tmp_path / "c.sqlite3"))
    result = assistant.chat("Can you help?")
    assert result["requires_human_review"] is True
    assert result["refund_status"] == "NOT_CHECKED"


def test_assistant_routes_registered(monkeypatch) -> None:
    paths = {route.path for route in app.routes}
    assert "/api/assistant/chat" in paths
    assert "/api/assistant/refund" in paths
    from app.api import assistant_routes
    class FakeAssistant:
        def health(self):
            return {"status": "ok", "policy_documents": 1}
    monkeypatch.setattr(assistant_routes, "RAGAssistant", FakeAssistant)
    assert assistant_routes.health()["status"] == "ok"
