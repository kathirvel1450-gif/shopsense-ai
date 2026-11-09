"""Smoke tests for the service health route."""
import subprocess
import sys
from pathlib import Path

import pytest

from app.main import app, parse_cors_origins
from app.api.routes import health


def test_health_returns_service_status() -> None:
    assert health() == {"status": "ok", "service": "shopsense-ai-api"}
    assert any(route.path == "/api/health" for route in app.routes)


def test_cors_origins_default_to_local_vite_origins() -> None:
    assert parse_cors_origins(None) == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_cors_origins_parse_explicit_render_origin() -> None:
    assert parse_cors_origins(" https://shopsense-ai-dashboard.onrender.com/ , https://preview.example.com ") == [
        "https://shopsense-ai-dashboard.onrender.com", "https://preview.example.com",
    ]


def test_cors_origins_reject_wildcard() -> None:
    with pytest.raises(ValueError, match="explicit origins"):
        parse_cors_origins("*")


def test_fastapi_entrypoint_imports_from_repository_and_backend_roots() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    import_check = "from backend.main import app; assert app.title == 'ShopSense AI API'"
    subprocess.run([sys.executable, "-c", import_check], cwd=repository_root, check=True, capture_output=True, text=True)
    subprocess.run([sys.executable, "-c", "from main import app; assert app.title == 'ShopSense AI API'"], cwd=repository_root / "backend", check=True, capture_output=True, text=True)
