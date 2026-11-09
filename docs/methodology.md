# Methodology

## Data engineering

1. Discover CSVs in the configured raw folder and inspect each header.
2. Profile row and column counts, types, missingness, duplicates, distinct counts, distributions, numeric summaries, and parseable date ranges.
3. Apply configured reusable cleaning operations to a copy: exact duplicate handling, category normalization, missing-value rules, type conversion, date validation, and invalid-value checks.
4. Record every operation in audit output; preserve raw files and report outliers without silently deleting valid observations.
5. Generate charts only when matching columns exist, validate cleaned tables, and load supported records into SQLite.

## RFM and K-Means

The pipeline selects completed orders using the configured status values and dynamically maps customer, order, date, and amount columns. Recency is calculated against a pinned reference date for reproducibility. Frequency counts distinct completed order identifiers; monetary sums valid completed-order amounts. Customers without completed orders are represented explicitly.

RFM IDs are kept outside the feature matrix. Invalid/non-finite values are handled before `StandardScaler` fits on the available RFM records. K-Means candidates K=2 through 8 use fixed randomness and repeat count. Inertia measures within-cluster squared distance and tends to decrease as K increases. Silhouette measures cluster separation/compactness on a -1 to 1 scale when feasible. Candidate selection considers scores and interpretability; the largest silhouette is not automatically a business-optimal answer. Segment names describe observed relative RFM profiles and are not forced labels.

The churn-risk indicator is a transparent recency/activity heuristic using configurable thresholds. It is not a supervised model: no labeled churn outcome is trained, no calibrated probability is produced, and a high-risk flag is not a claim that a customer will leave.

## Ticket processing and privacy

Ticket content is validated for type, emptiness, allowed size, malformed controls, and token budget. Identifiers and contact values are masked before prompts. Token counts use a compatible tokenizer when configured/available; fallback estimates are explicitly approximate. The model gateway builds prompts from sanitized text and validates returned categories and structured output. Classification categories and priority/team routing rules are documented in the Part C code and README. No accuracy claim is valid without labeled evaluation examples representative of real tickets.

## Retrieval-augmented generation

Markdown policy files are loaded with file/section references, split into overlapping chunks, embedded, and ranked for a sanitized question. Local hash embeddings capture lexical overlap; this is not semantic understanding. Optional provider embeddings can be enabled with credentials; optional Chroma can persist vectors. Retrieved references are supplied to a model through the central guardrail gateway, which validates the response and citations. When context is missing or weak, the assistant should avoid asserting unsupported policy. The checked-in policies are synthetic examples, so the system has no validated real-policy coverage.

## Evaluation and evidence

Unit tests validate transformation and rule behavior. Integration tests use isolated temporary fixtures to prove module wiring and persistence. These tests are not a substitute for evaluating on trainer data. Once approved data is supplied, document provenance, row counts, mapping decisions, exclusion counts, actual metrics, model configuration, and limitations separately from test fixtures.
