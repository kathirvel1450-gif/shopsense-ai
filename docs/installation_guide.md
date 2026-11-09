# Installation guide

## Prerequisites

- Python 3.10+ (the project was developed with Python 3.11).
- Node.js 20.19+ or 22.12+, plus npm (required by Vite 7).
- Git for version control.

## Backend setup (PowerShell)

From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If script execution is blocked, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the current terminal, then activate the environment. Optional dependencies (Jupyter, `tiktoken`, LangChain splitters, Chroma) are in `requirements-optional.txt`.

Edit `.env` only as needed. Do not commit it. Core settings include `DATABASE_URL`, `SHOPSENSE_RAW_DIR`, `SHOPSENSE_PROCESSED_DIR`, and `SHOPSENSE_OUTPUTS_DIR`. RAG settings include policy/index folders, chunk size/overlap, `RAG_TOP_K`, embedding provider, and conversation database. Credentials for external services belong only in backend environment variables, never in a `VITE_` setting.

## Start backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs`; health is at `/api/health`.

## Start frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Vite reads the project-root `.env` because `frontend/vite.config.js` sets `envDir`. Set `VITE_API_BASE_URL` there to override the default API origin, then restart Vite. Browser-visible variables must never contain private credentials.

## Add trainer data and run pipeline

Place authorized `customers.csv`, `orders.csv`, and `tickets.csv` under `datasets/raw/`. Start the backend and run `POST /api/data/cleaning` from the Swagger page, or from `backend/` run:

```powershell
python -c "from app.data_engine.pipeline import run_pipeline; print(run_pipeline())"
```

Raw inputs remain untouched. Review cleaning/profile reports before analysis. Data-derived artifacts are written to local processed/output locations, which are ignored by Git.

## Test and troubleshoot

```powershell
python -m pytest backend/tests tests -q
python -m compileall -q backend tests
python -m pip check
```

From `frontend/`, run `npm test`, `npm run build`, and `npm ls --depth=0`. Use `npm run dev -- --host 127.0.0.1` if local browser binding needs an explicit host. See [end-to-end testing](end_to_end_testing.md) for environment limits and [testing summary](testing_summary.md) for the latest recorded results.
