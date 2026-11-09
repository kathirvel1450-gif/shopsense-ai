"""FastAPI entrypoint usable from either the repository or backend directory."""
import sys
from pathlib import Path

# Application modules use the `app.*` package path. Ensure that package is
# discoverable when Uvicorn imports `backend.main:app` from the repository root.
_BACKEND_DIRECTORY = str(Path(__file__).resolve().parent)
if _BACKEND_DIRECTORY not in sys.path:
    sys.path.insert(0, _BACKEND_DIRECTORY)

from app.main import app

__all__ = ["app"]
