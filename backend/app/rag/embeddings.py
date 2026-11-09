"""Configured embeddings with a deterministic local lexical-hash fallback."""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx
import numpy as np
from dotenv import load_dotenv

from app.data_engine.pipeline import project_root


@dataclass(frozen=True)
class EmbeddingStatus:
    provider: str
    model: str
    semantic: bool
    fallback_used: bool
    fallback_reason: str | None = None


class LocalHashEmbeddings:
    """Stable signed feature-hash vectors; lexical similarity, not semantic AI."""
    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self.name = f"local-hash-v1-{dimensions}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text).tolist() for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text).tolist()

    def _vector(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimensions, dtype=np.float32)
        tokens = re.findall(r"[\w]+", text.casefold(), flags=re.UNICODE)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            index = number % self.dimensions
            sign = 1.0 if (number >> 16) & 1 else -1.0
            vector[index] += sign
        norm = float(np.linalg.norm(vector))
        if norm:
            vector /= norm
        return vector


class OpenAICompatibleEmbeddings:
    """OpenAI-compatible /embeddings adapter for policy and masked-query vectors."""
    def __init__(self, api_key: str, model: str, base_url: str, dimensions: int | None = None) -> None:
        self.api_key, self.model = api_key, model
        self.endpoint = base_url.rstrip("/") + "/embeddings"
        self.dimensions = dimensions
        self.name = f"openai-{model}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(self.endpoint, headers={"Authorization": f"Bearer {self.api_key}"}, json={"model": self.model, "input": texts}, timeout=45.0)
        response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        vectors = [item["embedding"] for item in data]
        if not vectors or any(not isinstance(value, (int, float)) for vector in vectors for value in vector):
            raise ValueError("Embedding provider returned malformed vectors.")
        self.dimensions = len(vectors[0])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class EmbeddingService:
    """Select configured provider and switch deterministically to local on errors."""
    def __init__(self, provider: Any | None = None, fallback_dimensions: int | None = None) -> None:
        load_dotenv(project_root() / ".env", override=False)
        self.fallback_reason: str | None = None
        if provider is not None:
            self.provider = provider
        else:
            requested = os.getenv("RAG_EMBEDDING_PROVIDER", "local-hash").casefold()
            embedding_key = os.getenv("RAG_EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
            if requested in {"openai", "openai-compatible"} and embedding_key:
                self.provider = OpenAICompatibleEmbeddings(
                    embedding_key, os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small"),
                    os.getenv("RAG_EMBEDDING_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")),
                )
            else:
                self.provider = LocalHashEmbeddings(fallback_dimensions or int(os.getenv("RAG_LOCAL_EMBEDDING_DIMENSIONS", "384")))
                if requested in {"openai", "openai-compatible"}:
                    self.fallback_reason = "OPENAI_API_KEY is not configured; using deterministic local hash vectors."
                elif requested not in {"local", "local-hash", "mock"}:
                    self.fallback_reason = f"Embedding provider '{requested}' is unsupported; using deterministic local hash vectors."

    @property
    def provider_name(self) -> str:
        return str(self.provider.name)

    @property
    def status(self) -> EmbeddingStatus:
        local = isinstance(self.provider, LocalHashEmbeddings)
        return EmbeddingStatus(self.provider_name, self.provider_name, not local, self.fallback_reason is not None, self.fallback_reason)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return self.provider.embed_documents(texts)
        except Exception as exc:
            self._fallback(exc)
            return self.provider.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        try:
            return self.provider.embed_query(text)
        except Exception as exc:
            self._fallback(exc)
            return self.provider.embed_query(text)

    def _fallback(self, exc: Exception) -> None:
        self.fallback_reason = f"Configured embedding provider unavailable ({type(exc).__name__}); using deterministic local hash vectors."
        self.provider = LocalHashEmbeddings(int(os.getenv("RAG_LOCAL_EMBEDDING_DIMENSIONS", "384")))


def embedding_configuration() -> dict[str, Any]:
    """Return configured selection without secrets."""
    service = EmbeddingService()
    return {"provider": service.status.provider, "model": service.status.model, "semantic": service.status.semantic, "fallback_used": service.status.fallback_used, "fallback_reason": service.status.fallback_reason}
