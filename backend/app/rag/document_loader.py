"""Load local policy Markdown and preserve section/source metadata."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PolicyDocument:
    page_content: str
    metadata: dict[str, Any]


def load_policy_documents(policy_dir: Path) -> list[PolicyDocument]:
    """Load UTF-8 Markdown policies, split by headings, and mark synthetic text."""
    policy_dir = Path(policy_dir)
    if not policy_dir.exists():
        return []
    documents: list[PolicyDocument] = []
    for path in sorted(policy_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        sections = _split_sections(text)
        for section, content in sections:
            if not content.strip():
                continue
            documents.append(PolicyDocument(
                page_content=content.strip(),
                metadata={
                    "source_name": path.name,
                    "source_ref": f"{path.name}#{_slug(section)}",
                    "section": section,
                    "synthetic_policy": "Synthetic Demonstration Policy" in text or "Fictional demonstration content" in text,
                },
            ))
    return documents


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = "Overview"
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = re.sub(r"^#+\s*", "", line).strip() or "Overview"
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "section"
