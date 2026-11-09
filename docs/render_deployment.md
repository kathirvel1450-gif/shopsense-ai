# Render deployment preparation

This project is configured for two Render services: a FastAPI web service and a React/Vite static site. The root `render.yaml` is a Render Blueprint. It does not deploy by itself; the owner must connect the GitHub repository in Render and explicitly create/sync the Blueprint. Automatic deploys after the initial setup are disabled in the Blueprint.

## Actual entrypoints and commands

- FastAPI application object: `app` imported from `backend/main.py`, which re-exports `backend/app/main.py`.
- Render backend start command from the repository root: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- Backend build command: `pip install -r requirements.txt`.
- Vite build command in `frontend/`: `npm ci && npm run build`.
- Static publish directory relative to the frontend service root: `dist`.
- The frontend reads `import.meta.env.VITE_API_BASE_URL`, trims a trailing slash, and falls back to localhost only when the variable is unset. Render must receive this variable **at build time**.
- The API allows the two local Vite origins by default. Set `CORS_ORIGINS` to exact comma-separated origins, including `https://` and no path, for the deployed frontend.

Render's FastAPI guide uses `uvicorn main:app --host 0.0.0.0 --port $PORT`; this repository's start command uses `backend.main:app` from the repo root. `backend/main.py` adds the backend directory to Python's import search path before importing `app.main`, so the existing `app.*` imports resolve. This also preserves local startup via `cd backend` followed by `python -m uvicorn main:app --reload`. Render's Vite static-site setup uses `npm ci && npm run build` and `dist`. Its rewrite rule supports client-side React Router URLs. See the official [FastAPI deployment guide](https://render.com/docs/deploy-fastapi), [static sites](https://render.com/docs/static-sites), [monorepo support](https://render.com/docs/monorepo-support), [rewrites](https://render.com/docs/redirects-rewrites), and [environment variables](https://render.com/docs/configure-environment-variables).

## Setup steps

1. Review local changes and commit/push them to the connected GitHub branch only when you authorize that step. No push or deployment was performed while preparing this file.
2. In Render, choose **New → Blueprint**, connect `https://github.com/kathirvel1450-gif/shopsense-ai`, and select the `master` branch containing `render.yaml`.
3. Create the two services in the Blueprint. The backend service uses the repository root for dependency installation and starts with the command above. The static service uses `frontend/` as its root and publishes `dist`. The Blueprint references each service's public `RENDER_EXTERNAL_URL`: it supplies `VITE_API_BASE_URL` to the frontend build and `CORS_ORIGINS` to the backend, without hardcoding hostnames.
4. After both services finish their first deploy, copy their actual URLs from the Render dashboard. Verify the backend at `https://<actual-api-service>.onrender.com/api/health` and open the static-site URL. Confirm the dashboard reports API connected. Test a direct refresh on `/customers` or another dashboard route.
5. If you later change a service's assigned URL or custom domain, sync the Blueprint so the referenced environment values refresh. You can also set the exact values manually in each service's **Environment** page.

Do not place API keys in the frontend variables. No API key is needed for the deterministic local mock mode. The Blueprint contains only public service URL references and non-secret runtime settings.

## Storage and policies

The checked-in Markdown policy files are present in the backend service's repository checkout and load from `policies/`. They are synthetic demonstrations, not an actual retailer's terms. The default SQLite database, assistant conversation store, RAG index, processed CSVs, and reports are written to local project paths. Render's default filesystem is ephemeral; on free web services, local SQLite/index/conversation/output changes can disappear on redeploy, restart, or spin-down. Free web services cannot use persistent disks. This is acceptable for a no-data classroom preview, but do not treat it as durable storage. For persistent application data, move the database to a managed database such as Render Postgres (the SQLAlchemy layer accepts `DATABASE_URL`) or use a plan that supports an attached disk where appropriate.

Trainer datasets are not present. Deployment will show empty/missing-data states; do not upload or imply synthetic business results. No training data is required to verify the public dashboard shell, health route, mock assistant, and synthetic policy citations.

## Public access and provider behavior

The current API has no authentication layer. Anyone who can reach the public URL can call its API endpoints. Keep customer data out of this deployment and do not enter real tickets or credentials. The refund route is a human-review simulation and performs no real transaction.

With no `OPENAI_API_KEY`, ticket classification and assistant generation use the deterministic mock. Set `RAG_EMBEDDING_PROVIDER=local-hash` and `RAG_VECTOR_BACKEND=sqlite` as in the Blueprint for deterministic local lexical retrieval. Hash vectors are not semantic embeddings. Do not add a real provider key until you intentionally configure and secure the public service; never use a `VITE_` variable for a secret.

Render free web services spin down after 15 minutes idle and may take about a minute to wake on the next request; their filesystem is ephemeral. Static sites are served separately. See the official [free instance limitations](https://render.com/docs/free) and [persistent disk limitations](https://render.com/docs/disks).
