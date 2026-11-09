from app.rag.embeddings import EmbeddingService, LocalHashEmbeddings


def test_local_hash_vectors_are_stable_and_normalized() -> None:
    embedder = LocalHashEmbeddings(64)
    vector = embedder.embed_query("delayed package")
    assert vector == embedder.embed_query("delayed package")
    assert abs(sum(x*x for x in vector) - 1) < 1e-5


def test_embedding_service_accepts_explicit_mock() -> None:
    service = EmbeddingService(provider=LocalHashEmbeddings(32))
    assert service.status.semantic is False
    assert len(service.embed_query("refund")) == 32
