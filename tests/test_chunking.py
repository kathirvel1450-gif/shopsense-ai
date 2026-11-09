import pytest

from app.rag.chunking import compare_chunking_configurations, split_policy_documents
from app.rag.document_loader import PolicyDocument


def test_chunking_is_deterministic_and_overlapping() -> None:
    doc = PolicyDocument("refund terms " * 100, {"source_ref": "x#y", "source_name": "x", "section": "y", "synthetic_policy": True})
    first = split_policy_documents([doc], 120, 20)
    second = split_policy_documents([doc], 120, 20)
    assert [x.chunk_id for x in first] == [x.chunk_id for x in second]
    assert len(first) > 1
    assert first[0].metadata["chunk_overlap_chars"] == 20
    assert len(compare_chunking_configurations([doc])) == 3


def test_invalid_chunk_options_fail() -> None:
    with pytest.raises(ValueError):
        split_policy_documents([], 10, 10)
