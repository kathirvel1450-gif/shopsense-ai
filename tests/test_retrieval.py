from pathlib import Path

from app.rag.embeddings import EmbeddingService, LocalHashEmbeddings
from app.rag.retrieval import PolicyRetriever


def test_index_is_idempotent_and_retrieves_sources(tmp_path: Path) -> None:
    policies = tmp_path / "policies"
    policies.mkdir()
    (policies / "delivery_policy.md").write_text("# Synthetic Demonstration Policy\n\n## Delivery\n\nDelayed delivery packages can be checked with a carrier.", encoding="utf-8")
    retriever = PolicyRetriever(policy_dir=policies, persist_directory=tmp_path / "index", embeddings=EmbeddingService(LocalHashEmbeddings(64)))
    result = retriever.index()
    assert result["indexed_chunk_count"] > 0
    assert retriever.index()["indexed_chunk_count"] == result["indexed_chunk_count"]
    docs = retriever.retrieve("delayed delivery package")
    assert docs and docs[0]["source_ref"].startswith("delivery_policy.md#")
    assert docs[0]["synthetic_policy"] is True


def test_empty_policy_collection_is_safe(tmp_path: Path) -> None:
    retriever = PolicyRetriever(policy_dir=tmp_path / "empty", persist_directory=tmp_path / "index")
    assert retriever.retrieve("question") == []


def test_top_k_reads_positive_environment_setting(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RAG_TOP_K", "2")
    retriever = PolicyRetriever(policy_dir=tmp_path / "empty", persist_directory=tmp_path / "index")
    assert retriever.top_k == 2
