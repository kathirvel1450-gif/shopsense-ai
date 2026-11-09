"""Persistent Chroma vector storage with a SQLite cosine fallback if unavailable."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np

from app.rag.chunking import PolicyChunk


class PersistentVectorStore:
    """Use Chroma PersistentClient when installed, else a clearly named local fallback."""
    def __init__(self, persist_directory: Path) -> None:
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._client = None
        requested_backend = os.getenv("RAG_VECTOR_BACKEND", "auto").casefold()
        if requested_backend not in {"auto", "chromadb", "sqlite"}:
            raise ValueError("RAG_VECTOR_BACKEND must be auto, chromadb, or sqlite.")
        try:
            if requested_backend == "sqlite":
                raise ImportError("SQLite backend explicitly selected")
            import chromadb

            self._client = chromadb.PersistentClient(path=str(self.persist_directory))
            self.backend = "chromadb"
        except ImportError:
            self.backend = "sqlite_cosine_fallback"
            self._init_sqlite()

    def index_is_current(self, provider: str, fingerprint: str, chunk_ids: list[str]) -> bool:
        if self._client is not None:
            collection = self._get_collection(provider, create=False)
            if collection is None or collection.count() != len(chunk_ids):
                return False
            existing = collection.get(include=["metadatas"])
            return set(existing.get("ids", [])) == set(chunk_ids) and all((m or {}).get("index_fingerprint") == fingerprint for m in existing.get("metadatas", []))
        with self._connect() as db:
            rows = db.execute("SELECT chunk_id, metadata_json FROM policy_vectors WHERE provider = ?", (provider,)).fetchall()
        return len(rows) == len(chunk_ids) and {row[0] for row in rows} == set(chunk_ids) and all(json.loads(row[1]).get("index_fingerprint") == fingerprint for row in rows)

    def upsert_chunks(self, provider: str, chunks: list[PolicyChunk], vectors: list[list[float]], fingerprint: str, rebuild: bool = False) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("Every policy chunk needs exactly one embedding vector.")
        if not chunks:
            return 0
        if self.index_is_current(provider, fingerprint, [chunk.chunk_id for chunk in chunks]) and not rebuild:
            return len(chunks)
        if self._client is not None:
            old = self._get_collection(provider, create=False)
            if old is not None:
                self._client.delete_collection(old.name)
            collection = self._client.get_or_create_collection(
                name=self._collection_name(provider),
                metadata={"hnsw:space": "cosine", "embedding_provider": provider, "index_fingerprint": fingerprint},
            )
            collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                documents=[chunk.page_content for chunk in chunks],
                metadatas=[{**_safe_metadata(chunk.metadata), "index_fingerprint": fingerprint} for chunk in chunks],
                embeddings=vectors,
            )
        else:
            with self._connect() as db:
                db.execute("DELETE FROM policy_vectors WHERE provider = ?", (provider,))
                db.executemany(
                    "INSERT INTO policy_vectors(provider, chunk_id, document, metadata_json, embedding_json) VALUES (?, ?, ?, ?, ?)",
                    [(provider, chunk.chunk_id, chunk.page_content, json.dumps({**_safe_metadata(chunk.metadata), "index_fingerprint": fingerprint}), json.dumps(vector)) for chunk, vector in zip(chunks, vectors)],
                )
        return len(chunks)

    def search(self, provider: str, query_vector: list[float], top_k: int = 4) -> list[dict[str, Any]]:
        if self._client is not None:
            collection = self._get_collection(provider, create=False)
            if collection is None or collection.count() == 0:
                return []
            response = collection.query(query_embeddings=[query_vector], n_results=min(max(1, top_k), collection.count()), include=["documents", "metadatas", "distances"])
            ids = response.get("ids", [[]])[0]
            docs = response.get("documents", [[]])[0]
            metadatas = response.get("metadatas", [[]])[0]
            distances = response.get("distances", [[]])[0]
            return [{"chunk_id": chunk_id, "page_content": doc, "metadata": metadata or {}, "score": float(1.0 - distance)} for chunk_id, doc, metadata, distance in zip(ids, docs, metadatas, distances)]
        with self._connect() as db:
            rows = db.execute("SELECT chunk_id, document, metadata_json, embedding_json FROM policy_vectors WHERE provider = ?", (provider,)).fetchall()
        query = np.asarray(query_vector, dtype=float)
        results = []
        for chunk_id, document, metadata_json, embedding_json in rows:
            vector = np.asarray(json.loads(embedding_json), dtype=float)
            denom = float(np.linalg.norm(query) * np.linalg.norm(vector))
            score = float(np.dot(query, vector) / denom) if denom else 0.0
            results.append({"chunk_id": chunk_id, "page_content": document, "metadata": json.loads(metadata_json), "score": score})
        return sorted(results, key=lambda item: item["score"], reverse=True)[:max(1, top_k)]

    def count(self, provider: str) -> int:
        if self._client is not None:
            collection = self._get_collection(provider, create=False)
            return collection.count() if collection is not None else 0
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM policy_vectors WHERE provider = ?", (provider,)).fetchone()[0])

    def _get_collection(self, provider: str, create: bool):
        name = self._collection_name(provider)
        if create:
            return self._client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine", "embedding_provider": provider})
        try:
            return self._client.get_collection(name=name)
        except Exception:
            return None

    @staticmethod
    def _collection_name(provider: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", provider).strip("_- ").lower()
        return f"policy_{slug or 'default'}"[:60]

    def _init_sqlite(self) -> None:
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS policy_vectors (provider TEXT NOT NULL, chunk_id TEXT NOT NULL, document TEXT NOT NULL, metadata_json TEXT NOT NULL, embedding_json TEXT NOT NULL, PRIMARY KEY(provider, chunk_id))")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.persist_directory / "vector_fallback.sqlite3", timeout=30)
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Keep Chroma metadata scalar-only and avoid storing arbitrary source objects."""
    return {str(key): value for key, value in metadata.items() if isinstance(value, (str, int, float, bool)) and value is not None}
