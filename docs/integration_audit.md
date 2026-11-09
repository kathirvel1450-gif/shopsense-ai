# Phase 8 integration audit

## Scope and result

The audit covered the FastAPI application and router registration, data pipeline, SQLite persistence, customer intelligence, ticket guardrails, policy retrieval/assistant flow, frontend API service and Vite configuration. The route inventory is checked against generated OpenAPI by `tests/test_system_integration.py`. Frontend component tests exercise the six dashboard views, navigation, and mocked API contracts.

No trainer CSVs are present in `datasets/raw/` or `datasets/processed/`; each contains only `.gitkeep`. The test suite creates controlled CSV and Markdown fixtures under pytest's temporary directory. Those fixtures verify integration behavior and are not business data or analytical evidence.

## Integration corrections

- Vite now loads environment variables from the repository root, matching the documented `.env.example` workflow and `VITE_API_BASE_URL` setting.
- Core Python dependencies are separated from optional integrations in `requirements-optional.txt`. SQLite retrieval and local hash embeddings remain available without Chroma or LangChain; Jupyter and `tiktoken` are optional.
- `RAG_TOP_K` now controls default retrieval depth, with safe fallback to 4 for invalid values. Unused RAG settings were removed from `.env.example`; the configured minimum-similarity setting is retained.
- Database validation in the integration fixture verifies inserted table counts, schema presence, and an empty SQLite `foreign_key_check` result.
- Customer API summaries are checked for aggregate-only output. Ticket and assistant responses are checked for fixture email leakage. Refund requests remain human review only and do not execute transactions.

## API / UI surface

Registered routes include system health, dataset availability, profiling, cleaning, EDA, database statistics, customer RFM/segments/churn risk/evaluation/summary, ticket validate/classify/process/summary, and assistant health/retrieve/chat/refund/escalate. These are compared to the generated OpenAPI schema in the integration test. The frontend API client uses matching paths and payload keys for dashboard interactions. CORS allows the two local Vite origins (`localhost:5173` and `127.0.0.1:5173`).

The dashboard pages are Overview, Data Quality, Customer Intelligence, Support Intelligence, AI Assistant, and Settings. The dashboard uses API responses for metrics and renders empty or unavailable states when sources are missing. Revenue is not exposed as an aggregate API metric. The older FreshKart storefront remains a separate Vite entry.

## Configuration and security review

- `.env.example` contains placeholders, not real credentials. `.env` is ignored by Git. Vite exposes only variables prefixed `VITE_` to browser code; backend credentials remain server-side.
- Ticket text is guarded and masked before model-facing requests; ticket APIs omit raw ticket text. Assistant prompts and persisted turns use sanitized user content. No authentication/authorization layer or production deployment configuration is included; run this foundation only in the intended local/training environment until those controls are designed.
- The default assistant provider is a deterministic local mock; default local-hash vectors are lexical similarity, not semantic embeddings. Actual external-provider operation requires valid provider configuration and credentials.
- `requirements.txt` lists core runtime and test packages. `requirements-optional.txt` covers token counting, notebook tooling, LangChain splitting, and Chroma.

## Known integration limits

- No real customer, order, or ticket rows exist here, so no real RFM, segmentation, ticket classifications, churn indicators, or revenue results can be reported.
- The Phase 8 integration test calls the actual registered endpoint handler functions directly and checks OpenAPI/CORS configuration. Starlette `TestClient` hangs in this Windows environment even on a minimal one-route FastAPI app, so HTTP serialization, status codes, middleware execution, and network transport were not verified by that test.
- A prior attempt to open the local Vite development server in the desktop browser timed out. Build and component checks verify the frontend, but a live browser session against the local backend was not demonstrated.
- External embedding/chat providers and live refund/order systems were not configured or called.
