"""Deterministic policy chunking using LangChain's recursive splitter when present."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.rag.document_loader import PolicyDocument


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    page_content: str
    metadata: dict[str, Any]


def split_policy_documents(
    documents: list[PolicyDocument],
    chunk_size: int = 600,
    chunk_overlap: int = 100,
) -> list[PolicyChunk]:
    """Split policy sections by character count, carrying source metadata."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be a positive character count.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size.")
    split_items: list[tuple[str, dict[str, Any]]]
    splitter_name = "langchain_recursive_character"
    try:
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, add_start_index=True)
        langchain_docs = [Document(page_content=doc.page_content, metadata=dict(doc.metadata)) for doc in documents]
        pieces = splitter.split_documents(langchain_docs)
        split_items = [(item.page_content, {**item.metadata, "start_index": int(item.metadata.get("start_index", 0))}) for item in pieces]
    except ImportError:
        splitter_name = "local_recursive_fallback"
        split_items = []
        for document in documents:
            for start, text in _fallback_split(document.page_content, chunk_size, chunk_overlap):
                split_items.append((text, {**document.metadata, "start_index": start}))
    chunks: list[PolicyChunk] = []
    for text, metadata in split_items:
        if not text.strip():
            continue
        stable_meta = dict(metadata)
        stable_meta["chunker"] = splitter_name
        stable_meta["chunk_size_chars"] = chunk_size
        stable_meta["chunk_overlap_chars"] = chunk_overlap
        identity = f"{stable_meta.get('source_ref','')}|{stable_meta.get('start_index',0)}|{text}"
        chunk_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
        stable_meta["chunk_id"] = chunk_id
        chunks.append(PolicyChunk(chunk_id, text, stable_meta))
    return chunks


def compare_chunking_configurations(
    documents: list[PolicyDocument],
    configurations: tuple[tuple[int, int], ...] = ((350, 50), (600, 100), (900, 150)),
) -> list[dict[str, Any]]:
    """Compare size/overlap options using counts and lengths, not quality claims."""
    results = []
    for size, overlap in configurations:
        chunks = split_policy_documents(documents, size, overlap)
        lengths = [len(chunk.page_content) for chunk in chunks]
        results.append({"chunk_size_chars": size, "chunk_overlap_chars": overlap, "chunk_count": len(chunks), "mean_chunk_chars": round(sum(lengths) / len(lengths), 1) if lengths else 0})
    return results


def _fallback_split(text: str, size: int, overlap: int) -> list[tuple[int, str]]:
    """Character-safe recursive-ish splitter used only without LangChain extras."""
    pieces: list[tuple[int, str]] = []
    start = 0
    while start < len(text):
        limit = min(len(text), start + size)
        end = limit
        if limit < len(text):
            for separator in ("\n\n", "\n", ". ", " "):
                boundary = text.rfind(separator, start + size // 2, limit)
                if boundary > start:
                    end = boundary + len(separator)
                    break
        pieces.append((start, text[start:end]))
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return pieces
