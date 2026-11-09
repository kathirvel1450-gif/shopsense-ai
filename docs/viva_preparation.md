# Viva preparation: questions and answers

These short answers describe this repository's implementation. Explain limitations clearly; do not present test fixtures or synthetic policies as retailer results.

1. **What is Python used for here?** The backend and data/ML workflows are written in Python; FastAPI exposes them as API routes.
2. **What is Pandas?** A Python library for tabular data. Here it reads CSVs, profiles columns, and supports cleaning and feature preparation.
3. **Why preserve raw data?** Reproducibility and recovery: cleaning produces derived files so the source remains available for audit.
4. **What is EDA?** Exploratory data analysis: summaries and charts that help inspect distributions, missingness, dates, and relationships before conclusions.
5. **What is a primary key?** A column or column set that uniquely identifies a table row. The database layer applies candidate keys when the source schema supports them.
6. **What is a foreign key?** A constraint that links a child row to a valid parent row, such as an order's customer reference.
7. **Why SQLite?** It is a lightweight relational database suitable for a local academic prototype without a separate server.
8. **What does SQLAlchemy do?** It maps Python models and operations to SQL databases and helps keep database access structured.
9. **What is RFM?** Recency, Frequency, Monetary: how recently a customer ordered, how many distinct completed orders they made, and how much they spent.
10. **Why count completed orders only?** Pending, cancelled, or failed orders should not be treated as completed purchase behavior; accepted statuses are configurable.
11. **What is StandardScaler?** It centers features and scales them to unit variance so features with larger numeric scales do not dominate distance-based clustering.
12. **Why scale RFM?** Monetary totals may be much larger numerically than frequency or recency; K-Means uses distances, so scale matters.
13. **What does K-Means do?** It groups points around K centroids by repeatedly assigning points and updating the centroids.
14. **What is inertia?** The sum of squared distances from samples to their assigned cluster centers; it normally drops as K increases, so the elbow plot is a heuristic.
15. **What is silhouette score?** A measure comparing a point's closeness to its own cluster with its closeness to another cluster. Higher is generally more separated, but business usefulness also matters.
16. **Why evaluate K=2–8?** It compares a fixed, manageable range of cluster counts. Feasibility depends on sample size and distinct features.
17. **How are segment labels chosen?** They are descriptive summaries based on observed cluster-level RFM profiles. A label is not forced when the profile does not support it.
18. **Is churn risk a prediction?** No. It is a transparent inactivity/activity heuristic, not a supervised probability or forecast.
19. **What is a supervised model?** A model trained from labeled examples of input and expected outcome. This project has no labeled churn outcome dataset.
20. **What is NLP?** Natural language processing: methods for validating, classifying, or otherwise processing human language.
21. **What is zero-shot classification?** Assigning a category using category definitions without providing labeled training examples in that prompt.
22. **What is few-shot classification?** Including a small number of illustrative labeled examples in the prompt. They guide format/meaning but do not establish accuracy.
23. **What is PII?** Personally identifiable information, such as email addresses, phone numbers, and customer/order identifiers that could identify a person or case.
24. **Why mask PII before a model call?** To reduce unnecessary disclosure. The gateway masks sensitive values before prompt construction and keeps routing identifiers application-side when required.
25. **What is tokenization?** Splitting text into units a model tokenizer counts as tokens. Tokens are not the same as characters or words.
26. **Why set a token limit?** To bound cost/context and reject oversized input before it reaches the model. A word-piece fallback is an estimate, not an exact provider token count.
27. **What is an LLM?** A large language model that generates text from an input context. It can be wrong, so the system validates output and grounds answers in policy evidence.
28. **What is an embedding?** A numeric vector representing text so similarity can be calculated. Local hash vectors here capture lexical overlap and are not semantic embeddings.
29. **What is chunking?** Splitting long policy text into smaller overlapping pieces so relevant passages can be searched and cited.
30. **What is a vector database?** A system that stores vectors and searches for similar vectors. This project supports optional Chroma and a local SQLite fallback.
31. **What is RAG?** Retrieval-augmented generation: retrieve relevant documents first, then give those passages to a language model to ground its answer.
32. **What does LangChain do here?** Optional LangChain text splitters can split documents; a local splitter fallback is available. It is not required for the core local flow.
33. **What is FastAPI?** A Python web framework for typed HTTP endpoints and generated OpenAPI documentation.
34. **What is React?** A JavaScript UI library that builds the dashboard from reusable components and page state.
35. **How does the frontend integrate with FastAPI?** `frontend/src/services/api.js` centralizes fetch requests, API paths, JSON payloads, and error handling.
36. **What is CORS?** A browser rule controlling which web origins may call an API. Local Vite origins are allowed; CORS is not authentication.
37. **How do tests differ from real data evaluation?** Tests verify code behavior with controlled fixtures. They do not measure business outcomes or model accuracy on the trainer's data.
38. **Why a mock LLM?** It supports deterministic offline development without external credentials, but it is not evidence of real model quality.
39. **What happens for refunds?** The route records a human-review simulation; it cannot query orders or execute a transaction.
40. **How is Git different from GitHub?** Git is local version control; GitHub hosts remote repositories and collaboration workflows. This workspace has no commit history or configured remote yet.
41. **Why use branches?** Branches isolate work or submission parts. They should be created from a reviewed committed baseline so changes can be compared safely.
42. **What should be said about missing data?** State that the actual trainer dataset is absent, so data-dependent results remain pending; never substitute test fixtures for actual results.
