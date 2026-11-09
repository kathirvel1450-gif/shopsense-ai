"""SQLite conversation sessions storing PII-masked messages only."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.guardrails.pii_masking import mask_pii


class ConversationStore:
    """Persist masked turns, escalation records, and simulated refund states."""
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def create_conversation_id(self, conversation_id: str | None = None) -> str:
        """Create a conversation ID or validate a caller-provided UUID."""
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        try:
            return str(uuid.UUID(str(conversation_id)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("conversation_id must be a UUID.") from exc

    def save_turn(self, conversation_id: str, user_text: str, assistant_text: str) -> None:
        """Store sanitized messages; raw PII is masked again at persistence boundary."""
        conversation_id = self.create_conversation_id(conversation_id)
        now = _now()
        safe_user = mask_pii(user_text).sanitized_text
        safe_assistant = mask_pii(assistant_text).sanitized_text
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO conversations(conversation_id, created_at, updated_at) VALUES (?, ?, ?)", (conversation_id, now, now))
            db.execute("UPDATE conversations SET updated_at = ? WHERE conversation_id = ?", (now, conversation_id))
            db.executemany("INSERT INTO conversation_messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)", [(conversation_id, "user", safe_user, now), (conversation_id, "assistant", safe_assistant, now)])

    def history(self, conversation_id: str, limit: int = 8) -> list[dict[str, str]]:
        """Return recent masked turns in chronological order."""
        conversation_id = self.create_conversation_id(conversation_id)
        with self._connect() as db:
            rows = db.execute("SELECT role, content FROM conversation_messages WHERE conversation_id = ? ORDER BY message_id DESC LIMIT ?", (conversation_id, min(max(1, limit), 20))).fetchall()
        return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

    def record_escalation(self, conversation_id: str, reason_code: str, summary: str = "") -> str:
        """Persist a minimal escalation case without raw ticket/question text."""
        conversation_id = self.create_conversation_id(conversation_id)
        escalation_id = str(uuid.uuid4())
        safe_summary = mask_pii(summary).sanitized_text[:500]
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO conversations(conversation_id, created_at, updated_at) VALUES (?, ?, ?)", (conversation_id, _now(), _now()))
            db.execute("INSERT INTO assistant_escalations(escalation_id, conversation_id, reason_code, safe_summary, status, created_at) VALUES (?, ?, ?, ?, ?, ?)", (escalation_id, conversation_id, reason_code, safe_summary, "HUMAN_REVIEW", _now()))
        return escalation_id

    def record_refund(self, conversation_id: str, safe_summary: str, state: str, reason: str, states: list[str]) -> str:
        """Record a simulated refund workflow with no payment side effect."""
        conversation_id = self.create_conversation_id(conversation_id)
        request_id = str(uuid.uuid4())
        safe_summary = mask_pii(safe_summary).sanitized_text[:500]
        with self._connect() as db:
            db.execute("INSERT INTO simulated_refund_requests(request_id, conversation_id, safe_summary, state, reason, state_history_json, simulated_only, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)", (request_id, conversation_id, safe_summary, state, reason, json.dumps(states), _now(), _now()))
        return request_id

    def apply_simulated_refund_decision(self, request_id: str, approved: bool, reviewer_reference: str) -> dict[str, Any]:
        """Apply a demo-only human decision; this is not an authenticated public API."""
        if not reviewer_reference.strip():
            raise ValueError("A human reviewer reference is required for the simulation.")
        target = "SIMULATED_REFUND_APPROVED" if approved else "SIMULATED_REFUND_REJECTED"
        with self._connect() as db:
            row = db.execute("SELECT state, state_history_json FROM simulated_refund_requests WHERE request_id = ?", (request_id,)).fetchone()
            if row is None:
                raise KeyError("Simulated refund request not found.")
            if row[0] not in {"APPROVAL_REQUIRED", "HUMAN_REVIEW"}:
                raise ValueError("Refund simulation is not awaiting human review.")
            history = json.loads(row[1])
            history.append(target)
            db.execute("UPDATE simulated_refund_requests SET state = ?, state_history_json = ?, updated_at = ? WHERE request_id = ?", (target, json.dumps(history), _now(), request_id))
        return {"request_id": request_id, "state": target, "state_history": history, "simulated_only": True, "real_refund_processed": False}

    def refund_record(self, request_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT request_id, conversation_id, safe_summary, state, reason, state_history_json, simulated_only FROM simulated_refund_requests WHERE request_id = ?", (request_id,)).fetchone()
        if row is None:
            return None
        return {"request_id": row[0], "conversation_id": row[1], "safe_summary": row[2], "state": row[3], "reason": row[4], "state_history": json.loads(row[5]), "simulated_only": bool(row[6])}

    def _create_schema(self) -> None:
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS conversations (conversation_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS conversation_messages (message_id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id), role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_conversation_messages ON conversation_messages(conversation_id, message_id)")
            db.execute("CREATE TABLE IF NOT EXISTS assistant_escalations (escalation_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id), reason_code TEXT NOT NULL, safe_summary TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS simulated_refund_requests (request_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id), safe_summary TEXT NOT NULL, state TEXT NOT NULL, reason TEXT NOT NULL, state_history_json TEXT NOT NULL, simulated_only INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.database_path, timeout=30)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
