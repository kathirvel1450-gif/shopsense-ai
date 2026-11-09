# 10-minute ShopSense AI demonstration

## Preparation

- Use a local run with the backend and Vite running, or present the test suite and code if this machine cannot connect to the services.
- Capture only genuine screens. No trainer CSVs exist in this project. State when a page is empty because data is missing.
- The checked-in policy documents are synthetic demonstration policies. The default model is deterministic mock mode and default retrieval is lexical.

## Talk track and timing

| Time | Segment | Presenter actions and script |
|---|---|---|
| 0:00–0:50 | Business problem | “Retail teams need consistent data analysis and safe support workflows. This project connects those tasks while keeping raw data intact and directing sensitive cases to people.” State that actual trainer data is not included. |
| 0:50–1:40 | Architecture | Show the architecture diagram and dashboard. Explain React → FastAPI → data/ML/guardrail/RAG modules → SQLite, with one central guarded model gateway. |
| 1:40–2:50 | Data quality | Open Data Quality. Show missing-data/empty state if no CSVs are supplied. Explain that authorized CSVs go in `datasets/raw/`; profiling, cleaning audits, charts, and processed outputs are generated locally. If using the integration test, explicitly label its data as temporary test fixtures, not real records. |
| 2:50–4:15 | Customer intelligence | Open Customer Intelligence or explain RFM with the methodology document. Define recency/frequency/monetary, scaling, K=2–8, inertia and silhouette. Emphasize that no real K or segment is reportable without trainer data. |
| 4:15–5:45 | Guardrails | Open Support Intelligence or Swagger. Demonstrate validation/masking with a fictional email typed solely for demonstration; show the masked result and category/routing metadata. Do not use actual customer PII. Explain token constraints and model gateway. |
| 5:45–7:35 | RAG assistant | Ask a policy question such as “How should a delayed delivery be reviewed?” Show citations. Point out that displayed policies are synthetic and hash-vector mode is lexical, not semantic. If using a mock response, identify it as deterministic mock output. |
| 7:35–8:25 | Refund simulation | Submit a refund-related question and show the human-review state. Explain that no refund is approved or executed and there is no live order/payment integration. |
| 8:25–9:15 | Human escalation | Trigger or describe escalation. Explain safe summary masking and why fraud/payment concerns require review. |
| 9:15–10:00 | Quality and conclusion | Show passing test output and docs. Summarize implemented foundations, actual limitations (dataset, live provider, HTTP/browser verification), and next step: validate with trainer files and approved policies. |

## Closing statement

“ShopSense AI demonstrates an integrated and testable foundation. The repository does not contain actual customer data, and its demonstration policies and mock AI modes are not business evidence. The next academic step is to validate the pipeline with the trainer dataset and approved policies.”
