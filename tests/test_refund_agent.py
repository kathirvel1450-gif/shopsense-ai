from pathlib import Path

from app.rag.conversation import ConversationStore
from app.rag.embeddings import EmbeddingService, LocalHashEmbeddings
from app.rag.pipeline import RAGAssistant
from app.rag.refund_agent import RefundAgent
from app.rag.retrieval import PolicyRetriever


def test_refund_flow_stops_for_human_and_never_executes(tmp_path: Path) -> None:
    policies = tmp_path / "policies"
    policies.mkdir()
    (policies / "refund_policy.md").write_text("# Synthetic Demonstration Policy\n\n## Refund\n\nRefunds need authorized review.", encoding="utf-8")
    assistant = RAGAssistant(PolicyRetriever(policies, tmp_path / "index", embeddings=EmbeddingService(LocalHashEmbeddings(64))), conversation_store=ConversationStore(tmp_path / "c.sqlite3"))
    agent = RefundAgent(assistant)
    result = agent.request("I want a refund")
    assert result["refund_state"] == "HUMAN_REVIEW"
    assert result["refund_executed"] is False
    demo = agent.apply_demo_human_decision(result["request_id"], True, "review-1")
    assert demo["refund_executed"] is False
    assert demo["simulated_only"] is True
