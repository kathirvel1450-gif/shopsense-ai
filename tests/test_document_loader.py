from pathlib import Path

from app.rag.document_loader import load_policy_documents


def test_load_synthetic_markdown_policy(tmp_path: Path) -> None:
    (tmp_path / "demo.md").write_text("# Synthetic Demonstration Policy\n\n## Refunds\n\nAsk for review.", encoding="utf-8")
    docs = load_policy_documents(tmp_path)
    assert len(docs) == 2
    assert docs[1].metadata["source_ref"] == "demo.md#refunds"
    assert docs[0].metadata["synthetic_policy"] is True


def test_missing_policy_directory_returns_empty(tmp_path: Path) -> None:
    assert load_policy_documents(tmp_path / "absent") == []
