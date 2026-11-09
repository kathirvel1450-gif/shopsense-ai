"""FastAPI application factory and health endpoint."""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import router
from app.api.customer_routes import router as customer_router
from app.api.ticket_routes import router as ticket_router
from app.api.assistant_routes import router as assistant_router

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def parse_cors_origins(value: str | None) -> list[str]:
    """Parse explicit comma-separated browser origins; avoid credentialed wildcard CORS."""
    if not value:
        return DEFAULT_CORS_ORIGINS.copy()
    origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
    if not origins:
        return DEFAULT_CORS_ORIGINS.copy()
    if "*" in origins:
        raise ValueError("CORS_ORIGINS must list explicit origins; wildcard CORS is not allowed.")
    return origins


app = FastAPI(title="ShopSense AI API", version="0.1.0", description="Retail customer intelligence and support API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(os.getenv("CORS_ORIGINS")),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")
app.include_router(customer_router, prefix="/api")
app.include_router(ticket_router, prefix="/api")
app.include_router(assistant_router, prefix="/api")


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": "ShopSense AI API", "docs": "/docs", "health": "/api/health"}
