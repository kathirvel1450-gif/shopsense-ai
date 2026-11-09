"""Smoke tests for the service health route."""
from app.main import app
from app.api.routes import health


def test_health_returns_service_status() -> None:
    assert health() == {"status": "ok", "service": "shopsense-ai-api"}
    assert any(route.path == "/api/health" for route in app.routes)
