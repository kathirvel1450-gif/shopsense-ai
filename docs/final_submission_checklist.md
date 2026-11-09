# Final submission checklist

Status checked for the current local project. Re-run the commands if code or dependencies change.

## Application and verification

- [x] Part A data engineering module is present.
- [x] Part B customer intelligence module is present.
- [x] Part C guardrails module is present.
- [x] Part D RAG assistant module is present.
- [x] README installation and launch commands match the current FastAPI entrypoint and Vite scripts.
- [x] Backend tests: `python -m pytest backend/tests tests -q` — **62 passed**.
- [x] Frontend tests: `npm test -- --reporter=dot` — **7 passed**.
- [x] Frontend production build: `npm run build` — **passed**.
- [x] Both notebooks parse as valid JSON and contain no stored cell outputs: `data_exploration.ipynb`, `customer_segmentation.ipynb`.
- [x] Core project and academic documentation are present, including the requirement map, methodology, install guide, testing summary, demo script, and viva questions.
- [x] No trainer CSVs are present in `datasets/raw/` or `datasets/processed/`; actual-data analysis is pending trainer files.
- [x] Mock LLM and lexical/local hash-vector retrieval limitations are disclosed in the README and project docs.
- [x] `.env` is absent; the submission archive excludes environment secrets, dependencies, caches, local databases, logs, and generated runtime outputs.
- [x] No GitHub push or publication was performed.

## Screenshots

- [ ] Genuine screenshots available: **none found in the project workspace**. No screenshots were fabricated and no placeholder images were created. Capture the dashboard/API/tests locally if screenshots are required by the instructor; use `docs/screenshot_checklist.md`.

## Before handing in

- [ ] Add the trainer-provided `customers.csv`, `orders.csv`, and `tickets.csv` only if they are supplied and permitted for submission.
- [ ] Run the pipeline and replace “analysis pending” with actual reviewed results only after validating those files.
- [ ] Confirm whether the instructor requires screenshots, a specific archive name, or a particular Git branch format.
