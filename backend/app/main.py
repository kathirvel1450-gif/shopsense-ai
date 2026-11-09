"""FastAPI application factory and health endpoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.customer_routes import router as customer_router
from app.api.ticket_routes import router as ticket_router
from app.api.assistant_routes import router as assistant_router

app = FastAPI(title="ShopSense AI API", version="0.1.0", description="Retail customer intelligence and support API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
