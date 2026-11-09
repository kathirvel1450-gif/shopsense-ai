from pathlib import Path
import sqlite3

from app.rag.conversation import ConversationStore
from app.rag.escalation import EscalationManager, escalation_reason


def test_fraud_escalates_and_persists_minimal_case(tmp_path: Path) -> None:
    assert escalation_reason("I suspect fraud on my account", []) == "fraud_or_account_security"
    store = ConversationStore(tmp_path / "c.sqlite3")
    manager = EscalationManager(store)
    session = store.create_conversation_id()
    case = manager.create(session, "fraud_or_account_security", "Suspected fraud, email a@example.com")
    assert case["status"] == "HUMAN_REVIEW"
    with sqlite3.connect(store.database_path) as db:
        summary = db.execute("SELECT safe_summary FROM assistant_escalations").fetchone()[0]
    assert "a@example.com" not in summary
