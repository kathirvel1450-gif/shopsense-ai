"""Cross-module integration checks using isolated, controlled test-only fixtures.

The Windows runner's Starlette TestClient hangs even for a one-route FastAPI app;
these tests invoke the registered endpoint functions directly and separately
verify the generated OpenAPI/CORS configuration.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import inspect

from app.api import assistant_routes, customer_routes, routes, ticket_routes
from app.api.assistant_routes import AssistantRequest, EscalationRequest
from app.api.routes import CleaningRequest
from app.api.ticket_routes import TicketRequest
from app.database.connection import get_engine
from app.main import app


@pytest.fixture
def isolated_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect every pipeline artifact and model provider to temporary resources."""
    raw = tmp_path / "raw"
    raw.mkdir()
    processed = tmp_path / "processed"
    outputs = tmp_path / "outputs"
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()
    database_path = tmp_path / "shopsense-integration.sqlite3"
    monkeypatch.setenv("SHOPSENSE_RAW_DIR", str(raw))
    monkeypatch.setenv("SHOPSENSE_PROCESSED_DIR", str(processed))
    monkeypatch.setenv("SHOPSENSE_OUTPUTS_DIR", str(outputs))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("RAG_POLICY_DIR", str(policy_dir))
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "rag-index"))
    monkeypatch.setenv("RAG_CONVERSATION_DB", str(tmp_path / "assistant.sqlite3"))
    monkeypatch.setenv("RAG_VECTOR_BACKEND", "sqlite")
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "local-hash")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("RAG_EMBEDDING_API_KEY", raising=False)

    customer_rows = []
    order_rows = []
    first_order = date(2026, 6, 1)
    for number in range(1, 11):
        customer_id = f"CUST-{number:04d}"
        customer_rows.append({"customer_id": customer_id, "gender": "Unknown", "city": "Test City", "signup_date": (date(2025, 1, 1) + timedelta(days=number)).isoformat()})
        for order_number, days_before in enumerate((number * 2 + 5, number * 3 + 15), start=1):
            order_rows.append({
                "order_id": f"ORD-{number:04d}-{order_number}", "customer_id": customer_id,
                "order_date": (first_order + timedelta(days=days_before)).isoformat(),
                "order_amount": float(number * 17 + order_number * 5), "order_status": "completed",
            })
    pd.DataFrame(customer_rows).to_csv(raw / "customers.csv", index=False)
    pd.DataFrame(order_rows).to_csv(raw / "orders.csv", index=False)
    pd.DataFrame([
        {"ticket_id": "T-001", "customer_id": "CUST-0001", "order_id": "ORD-0001-1", "ticket_text": "My delayed delivery is late; contact me at qa.person@example.test", "created_at": "2026-07-01", "ticket_status": "open"},
        {"ticket_id": "T-002", "customer_id": "CUST-0002", "order_id": "ORD-0002-1", "ticket_text": "The package arrived damaged", "created_at": "2026-07-02", "ticket_status": "open"},
    ]).to_csv(raw / "tickets.csv", index=False)
    (policy_dir / "delivery_policy.md").write_text(
        "# Synthetic Demonstration Policy\n\n## Delivery review\n\nFor a delayed delivery, check the carrier status through the retailer's official support channel. This example policy does not provide actual tracking information.\n",
        encoding="utf-8",
    )
    (policy_dir / "refund_policy.md").write_text(
        "# Synthetic Demonstration Policy\n\n## Refund review\n\nRefund requests require human review of the real order and terms. No refund is promised or processed by this example policy.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_data_database_ml_ticket_and_rag_integration(isolated_workspace: Path) -> None:
    # System and Phase 3 endpoints.
    assert routes.health()["status"] == "ok"
    availability = routes.dataset_availability()
    assert availability["dataset_count"] == 3 and all(availability["available"].values())
    profiling = routes.data_profiling()
    assert profiling["status"] == "complete" and profiling["datasets"]["customers"]["rows"] == 10
    eda = routes.data_eda()
    assert eda["chart_count"] > 0
    cleaning = routes.data_cleaning(CleaningRequest())
    assert cleaning["status"] == "complete"
    assert (Path(cleaning["processed_directory"]) / "customers.csv").is_file()
    stats = routes.database_stats()
    assert stats["exists"] and stats["tables"]["customers"]["rows"] == 10
    assert stats["tables"]["orders"]["rows"] == 20 and stats["tables"]["tickets"]["rows"] == 2
    database_path = isolated_workspace / "shopsense-integration.sqlite3"
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 10
    engine = get_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        assert "customer_id" in {column["name"] for column in inspect(engine).get_columns("orders")}
    finally:
        engine.dispose()

    # Phase 4 report routes consume the cleaned Phase 3 output.
    rfm = customer_routes.customers_rfm()
    segments = customer_routes.customers_segments()
    risk = customer_routes.customers_churn_risk()
    evaluation = customer_routes.customers_model_evaluation()
    summary = customer_routes.customers_summary()
    assert rfm["status"] == "complete" and rfm["customer_count"] == 10
    assert len(evaluation["evaluations"]) == 7
    assert summary["segment_count"] == len(segments["segments"])
    assert "not a supervised" in risk["method"].lower()
    assert "CUST-0001" not in str(summary)

    # Phase 5 ticket flow and Phase 6 retrieval, guarded chat, refund and escalation.
    invalid = ticket_routes.validate_ticket(TicketRequest(ticket_text="   "))
    assert invalid["valid"] is False
    ticket_text = "My delayed delivery order ORD-0001-1, email qa.person@example.test"
    valid = ticket_routes.validate_ticket(TicketRequest(ticket_text=ticket_text))
    assert valid["valid"] is True and valid["pii_mask_counts"]["email"] == 1
    classification = ticket_routes.classify_ticket(TicketRequest(ticket_text=ticket_text))
    assert classification["accepted"] is True and classification["category"] == "LATE_DELIVERY"
    assert "qa.person@example.test" not in str(classification)
    batch = ticket_routes.process_ticket()
    assert batch["ticket_rows"] == 2
    assert ticket_routes.ticket_summary()["classified_count"] == 2

    assistant_status = assistant_routes.health()
    assert assistant_status["llm_mode"] == "deterministic_mock"
    assert assistant_status["vector_backend"] == "sqlite_cosine_fallback"
    retrieved = assistant_routes.retrieve(AssistantRequest(question="How do I check a delayed delivery?"))
    assert retrieved["status"] == "retrieved" and retrieved["documents"]
    chat = assistant_routes.chat(AssistantRequest(question="How do I check a delayed delivery? qa.person@example.test"))
    assert chat["status"] in {"answered", "escalated"} and chat["citations"]
    assert "qa.person@example.test" not in str(chat)
    refund = assistant_routes.refund(AssistantRequest(question="I would like a refund"))
    assert refund["refund_state"] == "HUMAN_REVIEW" and refund["refund_executed"] is False
    escalation = assistant_routes.escalate(EscalationRequest(conversation_id=chat["conversation_id"], summary="Please review qa.person@example.test"))
    assert escalation["created"] is True and "qa.person@example.test" not in str(escalation)


def test_registered_openapi_and_frontend_cors_configuration() -> None:
    spec = app.openapi()
    expected = {
        "/api/health", "/api/datasets/availability", "/api/data/profiling", "/api/data/cleaning", "/api/data/eda",
        "/api/database/statistics", "/api/customers/rfm", "/api/customers/segments", "/api/customers/churn-risk",
        "/api/customers/model-evaluation", "/api/customers/summary", "/api/tickets/validate", "/api/tickets/classify",
        "/api/tickets/process", "/api/tickets/summary", "/api/assistant/health", "/api/assistant/retrieve",
        "/api/assistant/chat", "/api/assistant/refund", "/api/assistant/escalate",
    }
    assert expected.issubset(spec["paths"])
    cors = next(middleware for middleware in app.user_middleware if middleware.cls.__name__ == "CORSMiddleware")
    assert {"http://localhost:5173", "http://127.0.0.1:5173"}.issubset(set(cors.kwargs["allow_origins"]))
