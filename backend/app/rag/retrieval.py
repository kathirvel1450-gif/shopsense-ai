"""Policy indexing and top-k similarity search."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.data_engine.pipeline import configured_paths, project_root
from app.rag.chunking import PolicyChunk, compare_chunking_configurations, split_policy_documents
from app.rag.document_loader import load_policy_documents
from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import PersistentVectorStore


class PolicyRetriever:
    """Load policy chunks, persist vectors, and retrieve relevant evidence."""
    def __init__(
        self,
        policy_dir: Path | None = None,
        persist_directory: Path | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        top_k: int | None = None,
        minimum_similarity: float | None = None,
        embeddings: EmbeddingService | None = None,
        vector_store: PersistentVectorStore | None = None,
    ) -> None:
        load_dotenv(project_root() / ".env", override=False)
        paths = configured_paths()
        configured_policy = Path(os.getenv("RAG_POLICY_DIR", "policies"))
        configured_index = Path(os.getenv("RAG_INDEX_DIR", "outputs/chroma"))
        self.policy_dir = Path(policy_dir) if policy_dir is not None else (configured_policy if configured_policy.is_absolute() else project_root() / configured_policy)
        self.persist_directory = Path(persist_directory) if persist_directory is not None else (configured_index if configured_index.is_absolute() else project_root() / configured_index)
        self.chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "600")) if chunk_size is None else chunk_size
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
        self.top_k = top_k if top_k is not None else _env_positive_int("RAG_TOP_K", 4)
        self.minimum_similarity = float(os.getenv("RAG_MINIMUM_SIMILARITY", "0.05")) if minimum_similarity is None else minimum_similarity
        self.embeddings = embeddings or EmbeddingService()
        self.vector_store = vector_store or PersistentVectorStore(self.persist_directory)
        self.documents = load_policy_documents(self.policy_dir)
        self.chunks = split_policy_documents(self.documents, self.chunk_size, self.chunk_overlap)
        self.fingerprint = _fingerprint(self.chunks, self.chunk_size, self.chunk_overlap)
        self.indexed_count = 0
        self._indexed_provider: str | None = None

    def index(self, rebuild: bool = False) -> dict[str, Any]:
        """Idempotently index policy chunks; rebuild replaces the active collection."""
        if not self.chunks:
            self.indexed_count = 0
            return self.status()
        provider = self.embeddings.provider_name
        ids = [chunk.chunk_id for chunk in self.chunks]
        if not rebuild and self.vector_store.index_is_current(provider, self.fingerprint, ids):
            self.indexed_count = len(ids)
            self._indexed_provider = provider
            return self.status()
        vectors = self.embeddings.embed_documents([chunk.page_content for chunk in self.chunks])
        provider = self.embeddings.provider_name
        self.indexed_count = self.vector_store.upsert_chunks(provider, self.chunks, vectors, self.fingerprint, rebuild=rebuild)
        self._indexed_provider = provider
        return self.status()

    def retrieve(self, sanitized_query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """Retrieve top-k evidence by vector similarity; local hash mode is lexical."""
        self.index()
        if not self.chunks:
            return []
        query_vector = self.embeddings.embed_query(sanitized_query)
        if self._indexed_provider != self.embeddings.provider_name:
            self.index(rebuild=False)
        rows = self.vector_store.search(self.embeddings.provider_name, query_vector, top_k or self.top_k)
        results = []
        for row in rows:
            if row["score"] < self.minimum_similarity:
                continue
            results.append({
                "chunk_id": row["chunk_id"], "content": row["page_content"],
                "source_name": row["metadata"].get("source_name", "policy document"),
                "source_ref": row["metadata"].get("source_ref", "policy section"),
                "section": row["metadata"].get("section", ""),
                "synthetic_policy": bool(row["metadata"].get("synthetic_policy", False)),
                "similarity": round(float(row["score"]), 4),
            })
        return results

    def experiment_chunking(self) -> list[dict[str, Any]]:
        """Return count/length measurements for documented chunk configurations."""
        return compare_chunking_configurations(self.documents)

    def status(self) -> dict[str, Any]:
        """Describe actual embedding and storage mode without overstating semantics."""
        embedding_status = self.embeddings.status
        local = not embedding_status.semantic
        return {
            "document_count": len(self.documents), "chunk_count": len(self.chunks),
            "indexed_chunk_count": self.indexed_count or self.vector_store.count(self.embeddings.provider_name),
            "chunk_size_chars": self.chunk_size, "chunk_overlap_chars": self.chunk_overlap,
            "chunking_experiments": self.experiment_chunking(),
            "embedding_provider": embedding_status.provider, "embedding_model": embedding_status.model,
            "embedding_semantic": embedding_status.semantic, "fallback_used": embedding_status.fallback_used,
            "fallback_reason": embedding_status.fallback_reason,
            "vector_backend": self.vector_store.backend,
            "retrieval_mode": "deterministic local hash-vector similarity (lexical; not semantic)" if local else "configured dense embedding similarity",
            "synthetic_policies": all(bool(doc.metadata.get("synthetic_policy")) for doc in self.documents) if self.documents else True,
        }


def _fingerprint(chunks: list[PolicyChunk], size: int, overlap: int) -> str:
    digest = hashlib.sha256(f"{size}:{overlap}".encode())
    for chunk in chunks:
        digest.update(chunk.chunk_id.encode())
        digest.update(chunk.page_content.encode("utf-8"))
    return digest.hexdigest()


def _env_positive_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default
