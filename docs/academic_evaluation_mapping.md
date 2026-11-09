# Academic requirement mapping and branch plan

## Completion key

- **Implemented; actual data pending** means reusable code and tests exist, but trainer-data evidence is unavailable.
- **Implemented; provider setup pending** means local fallback exists; external service mode needs credentials and real evaluation.
- **Partially verified** means source/configuration is present but execution could not be demonstrated in this environment.

## Part A — Data Engineering (Phase 3)

| Assignment requirement | Implementation | API | Test | Evidence | Status |
|---|---|---|---|---|---|
| Discover expected CSVs and report missing files without generating substitutes | `backend/app/data_engine/ingestion.py`, `pipeline.py` | `GET /api/datasets/availability` | `tests/test_ingestion.py`, `test_pipeline.py` | Dataset availability response; raw folder remains empty | Implemented; actual data pending |
| Profile rows, columns, types, missingness, duplicates, unique/categorical/numeric/date summaries | `data_engine/profiling.py` | `GET /api/data/profiling` | `tests/test_profiling.py` | JSON report under `outputs/reports/` when run | Implemented; actual data pending |
| Reusable cleaning, city/gender normalization, missing/date/numeric/type handling, audit decisions | `data_engine/cleaning.py` | `POST /api/data/cleaning` | `tests/test_cleaning.py` | Processed CSV and cleaning audit in a configured data run | Implemented; actual data pending |
| EDA charts only when schema columns exist | `data_engine/eda.py` | `GET /api/data/eda` | `tests/test_pipeline.py` | Charts under `outputs/visualizations/` | Implemented; actual data pending |
| SQLite customers/orders/tickets, keys, relationships, indexes, validation | `database/models.py`, `connection.py`, `repository.py` | `GET /api/database/statistics` | `tests/test_database.py`, `test_system_integration.py` | Temporary database row/FK checks in integration test | Implemented; actual data pending |
| Exploration notebook | `notebooks/data_exploration.ipynb` | N/A | Notebook is not an automated test | Notebook source | Present; requires supplied data to produce findings |

## Part B — Customer Intelligence (Phase 4)

| Assignment requirement | Implementation | API | Test | Evidence | Status |
|---|---|---|---|---|---|
| Consume cleaned customers/orders and map columns; completed orders only | `customer_intelligence/rfm.py`, `pipeline.py` | `GET /api/customers/rfm` | `tests/test_rfm.py`, `test_customer_pipeline.py` | Temporary fixture flow only | Implemented; actual data pending |
| Reference date, customers without orders, invalid/missing value handling | `rfm.py`, `preprocessing.py` | RFM endpoint | `tests/test_rfm.py`, `test_preprocessing.py` | Reproducible unit cases | Implemented; actual data pending |
| StandardScaler, IDs outside features, model artifact | `preprocessing.py`, `pipeline.py` | Model evaluation endpoint | `tests/test_preprocessing.py`, `test_customer_pipeline.py` | Local artifact path configured under outputs | Implemented; actual data pending |
| K=2–8 inertia/silhouette, infeasible K handling, selection rationale | `clustering.py` | `GET /api/customers/model-evaluation` | `tests/test_clustering.py` | Test evaluation only; no real metric claimed | Implemented; actual data pending |
| Profile-based segment descriptions and customer output | `segmentation.py` | `GET /api/customers/segments`, `/summary` | `tests/test_segmentation.py`, `test_customer_api.py` | Aggregate API behavior | Implemented; actual data pending |
| Transparent inactivity risk; not supervised prediction | `churn_risk.py` | `GET /api/customers/churn-risk` | `tests/test_churn_risk.py` | Method explicitly documented as heuristic | Implemented; actual data pending |
| RFM/elbow/silhouette/cluster/PCA/segment/risk visuals | `visualization.py` | Summarized through customer APIs | `tests/test_customer_pipeline.py` | Generated only with compatible input | Implemented; actual data pending |
| Segmentation notebook | `notebooks/customer_segmentation.ipynb` | N/A | Notebook is not an automated test | Notebook source | Present; requires supplied data to show real findings |

## Part C — AI Guardrails (Phase 5)

| Assignment requirement | Implementation | API | Test | Evidence | Status |
|---|---|---|---|---|---|
| Validate input type, empty/whitespace, malformed, size, token limit; reject before model | `guardrails/validators.py`, `token_counter.py`, `model_gateway.py` | `POST /api/tickets/validate` | `tests/test_validators.py`, `test_token_counter.py`, `test_model_gateway.py` | Boundary/invalid-input tests | Implemented; tokenizer precision depends on optional package |
| Mask email, phone, order/customer identifiers before prompt/model log | `guardrails/pii_masking.py`, `prompt_builder.py` | Validate/classify/process routes | `tests/test_pii_masking.py`, `test_model_gateway.py` | PII leakage assertions | Implemented; actual policies/data require review |
| Zero-shot and few-shot classification over allowed categories | `classification.py`, `schemas.py` | `POST /api/tickets/classify`, `/process` | `tests/test_classification.py`, `test_ticket_pipeline.py` | Schema/category tests; mock mode only by default | Implemented; no accuracy claim |
| Priority and team routing, human review for sensitive tickets | `prioritization.py`, `routing.py` | Classification/process metadata | `tests/test_prioritization.py`, `test_routing.py` | Rules exercised by unit tests | Implemented |
| Central guarded model gateway and safe API summaries | `model_gateway.py`, `pipeline.py`, `api/ticket_routes.py` | `GET /api/tickets/summary` | `tests/test_model_gateway.py`, `test_ticket_api.py` | Model calls flow through gateway | Implemented; real provider setup pending |

## Part D — RAG Assistant (Phase 6)

| Assignment requirement | Implementation | API | Test | Evidence | Status |
|---|---|---|---|---|---|
| Load, inspect, chunk, reference policy documents | `rag/document_loader.py`, `chunking.py` | `POST /api/assistant/retrieve` | `tests/test_document_loader.py`, `test_chunking.py` | Synthetic demonstration policies only | Implemented; real retailer policy pending |
| Embeddings and persistent/vector fallback; top-k retrieval | `embeddings.py`, `vector_store.py`, `retrieval.py` | `GET /api/assistant/health`, retrieve | `tests/test_embeddings.py`, `test_retrieval.py` | Default local-hash + SQLite supported; optional Chroma | Implemented; lexical default |
| Masked query, grounded response, output/citation checks, safe memory | `rag/pipeline.py`, `response_generator.py`, `conversation.py`, `guardrails/model_gateway.py` | `POST /api/assistant/chat` | `tests/test_rag_pipeline.py` | Temporary policy integration test | Implemented; remote LLM setup pending |
| Refund simulation and human escalation | `refund_agent.py`, `escalation.py` | `POST /api/assistant/refund`, `/escalate` | `tests/test_refund_agent.py`, `test_escalation.py` | Refund remains human-review simulation | Implemented; no transaction integration |
| Assistant UI and conversation interaction | `frontend/src/pages/AIAssistant.jsx`, `services/api.js` | Assistant endpoints | `frontend/src/test/dashboard.test.jsx` | Component test; live browser unavailable | Partially verified |

## Cross-cutting integration and submission

| Requirement | Evidence | Status |
|---|---|---|
| FastAPI route registration, local CORS, connected data→database→ML→ticket→RAG workflow | `tests/test_system_integration.py`, generated OpenAPI | Handler integration passed; live HTTP transport unverified |
| Six dashboard pages, API service and error/empty states | `frontend/src/pages/`, API client, `frontend/src/test/` | 7 frontend tests passed; build passed; live browser unverified |
| API/dependency/config documentation | `README.md`, `.env.example`, requirements files, installation guide | Present; external credentials not configured |
| Genuine screenshots and trainer analysis | Local evidence checklist | Pending user capture and data supply |

## Branch preparation

### Observed Git state

The repository currently has an unborn `master` branch, no commits, no remote, and all project files appear untracked. The sandbox permits reading `.git` but not writing it; an attempted safe rename could not update `.git/HEAD` due to access denial. No files were staged, committed, discarded, or pushed. Thus, the branches below are a plan only; they do not yet exist.

### File ownership by academic part

- **Part A — `part-a-data-engineering`:** `backend/app/data_engine/`, `backend/app/database/`, data routes in `backend/app/api/routes.py`, `notebooks/data_exploration.ipynb`, Part A tests, dataset placeholders, and data dictionary/methodology docs.
- **Part B — `part-b-customer-intelligence`:** `backend/app/customer_intelligence/`, customer routes in `backend/app/api/customer_routes.py`, segmentation notebook, Part B tests, and RFM/methodology documentation.
- **Part C — `part-c-ai-guardrails`:** `backend/app/guardrails/`, ticket routes in `backend/app/api/ticket_routes.py`, Part C tests, and support/security methodology.
- **Part D — `part-d-rag-assistant`:** `backend/app/rag/`, assistant routes in `backend/app/api/assistant_routes.py`, synthetic policy examples, RAG tests, and RAG documentation.
- **Shared integration:** `backend/app/main.py`, `backend/main.py`, requirements and environment templates, `frontend/`, cross-module tests, root docs, README, `.gitignore`, outputs/datasets placeholders. These need an agreed shared baseline and may also receive small integration commits on each part branch.

### Recommended safe preparation sequence

1. Review and stage the entire current project as the initial local baseline on `main` after the owner confirms the desired commit attribution/message. This snapshot is currently uncommitted.
2. Create the four academic branches from the baseline and organize module-specific commits on each; merge/rebase decisions should be made explicitly and should not rewrite published history.
3. Add a GitHub remote only after repository owner, visibility, and URL are known; push only after explicit approval.

Because the repository has no commit object, Git cannot create normal named branches pointing to the current files without first creating a commit. The current managed sandbox also denies `.git` writes. No branch creation or commit was attempted beyond the blocked rename.

Once a baseline commit exists and `.git` is writable, local branch commands are:

```powershell
git switch main
git switch -c part-a-data-engineering
git switch main
git switch -c part-b-customer-intelligence
git switch main
git switch -c part-c-ai-guardrails
git switch main
git switch -c part-d-rag-assistant
```

These commands create branch names from the same baseline; module-specific commits should be applied deliberately rather than pretending the current empty history already contains them.
