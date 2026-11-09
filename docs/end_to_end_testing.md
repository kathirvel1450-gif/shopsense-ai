# End-to-end testing and local runbook

## Local prerequisites

- Python 3.10+ (project developed with Python 3.11).
- Node.js 20.19+ or 22.12+ and npm (Vite 7 requirement).
- Optional packages are listed separately in `requirements-optional.txt`.

From the repository root in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

To use optional notebook or retrieval integrations, run `pip install -r requirements-optional.txt`. Put valid API credentials only in the local ignored `.env` file if an external provider is intentionally enabled. Vite reads the root `.env`; restart Vite after changing `VITE_API_BASE_URL`.

## Run services

Terminal 1, from the repository root:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Backend docs: `http://127.0.0.1:8000/docs`. Health: `http://127.0.0.1:8000/api/health`.

Terminal 2, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL printed by the command. The dashboard API base defaults to `http://127.0.0.1:8000` and can be set with `VITE_API_BASE_URL` in the root `.env`.

## Verification commands

From the repository root:

```powershell
python -m pytest backend/tests tests -q
```

From `frontend/`:

```powershell
npm test -- --reporter=dot
npm run build
npm audit --offline
```

The integration test uses temporary controlled customers/orders/tickets and synthetic policy documents. It invokes route handler functions directly, checks the generated OpenAPI paths, verifies the configured CORS origins, and checks database relationships, downstream summaries, guardrail masking, and assistant response flow. It does not call a live HTTP server. In this environment, FastAPI `TestClient` stalls even for a minimal app, and the desktop browser did not connect to the local Vite server; transport and visual live-browser checks therefore remain unverified.

## Data handling and expected empty state

Place authorized `customers.csv`, `orders.csv`, and `tickets.csv` in `datasets/raw/`. Run `POST /api/data/cleaning` to profile, clean, validate, generate EDA outputs, and load SQLite. Raw files remain intact; derived files and database artifacts are local. Without trainer data, availability reports missing datasets, and the UI shows unavailable/empty states. Test fixtures are ephemeral and do not populate project data folders.

## Current limits

The local assistant defaults to a deterministic mock response and local hash-vector lexical search. Configure an authorized provider to use remote embeddings or language models. There is no live order lookup, refund execution, supervised churn model, or authentication layer. Synthetic policy documents in `policies/` must be replaced with approved retailer guidance before operational use.
