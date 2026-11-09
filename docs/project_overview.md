# Project overview

## What ShopSense AI demonstrates

ShopSense AI is a local full-stack academic project for retail data preparation, customer analysis, safe ticket handling, and policy-based support. It connects four modules behind a FastAPI service and a React dashboard.

## Problem and goals

Retail customer/order/ticket files can have inconsistent names, missing values, duplicates, and mixed formats. Teams also need transparent ways to summarize customer activity and answer support questions without sending personal details to a model. The project demonstrates schema-aware data workflows, interpretable clustering, explicit privacy guardrails, and cited policy retrieval.

## Four academic parts

1. **Part A — Data Engineering:** CSV ingestion, profiling, configurable cleaning, EDA, validation, and SQLite persistence.
2. **Part B — Customer Intelligence:** completed-order RFM, scaled K-Means evaluation, descriptive cluster labels, and heuristic inactivity-risk indicators.
3. **Part C — AI Guardrails:** validation, PII masking, token-aware checks, constrained classification, priority, routing, and a central model gateway.
4. **Part D — RAG Assistant:** policy loading, chunking, retrieval, gateway-protected responses, citations, refund review simulation, and escalation.

## Current evidence status

The repository contains no trainer CSVs. Integration fixtures used by pytest are created temporarily and are not an analysis dataset. The included policy files are synthetic examples. Therefore, the project demonstrates code paths and repeatable tests, but has no actual customer, order, ticket, segmentation, classification accuracy, or business outcome results.

## Start here

Install using [installation guide](installation_guide.md), understand the pipeline in [architecture](architecture.md) and [methodology](methodology.md), then consult [testing summary](testing_summary.md) and [academic evaluation mapping](academic_evaluation_mapping.md).
