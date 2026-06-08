# Analytics Copilot

Natural language analytics interface for dbt-modeled PostgreSQL data warehouses.

Ask a question in plain English. The system selects the right dbt mart model, generates a validated SQL query, runs it against a read-only PostgreSQL role, and returns structured results — no aggregation in the AI layer, no hallucinated column names.

## How It Works

```
User question (NL)
        │
        ▼
  FastAPI Gateway
        │
        ▼
  Redis Cache  ──── hit ────▶ return cached result
        │ miss
        ▼
  LangGraph Workflow
    [Intent Classifier]
         ↓
    [Schema Selector]   ← dbt manifest.json
         ↓
    [SQL Generator]     ← LangChain prompt + schema context
         ↓
    [SQL Validator]     ← column check + aggregation guard
         ↓ retry on fail (max 2)
    [SQL Executor]      ← PostgreSQL analyst_ro role
         ↓
    [Result Formatter]  → structured JSON
        │
        ▼
  Response (SQL + rows + NL explanation)
```

**Key design decision:** dbt handles all aggregation and joins in mart models. The AI layer only generates `SELECT ... FROM mart.* WHERE ... ORDER BY ... LIMIT ...` queries — nothing more.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13+, FastAPI, Uvicorn |
| AI Workflow | LangGraph, LangChain, OpenAI API |
| Data Modeling | dbt Core, dbt-postgres |
| Database | PostgreSQL |
| Cache | Redis |
| Observability | Langfuse, structured JSON logging |
| Infra | Docker Compose, uv |
| UI | Streamlit |

## Dataset

[Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 100k+ orders, 9 source tables, open license.

dbt model layers:
- **Staging** — type casting, column renaming: `stg_customers`, `stg_orders`, `stg_order_items`, `stg_products`, `stg_sellers`, `stg_reviews`
- **Intermediate** — joins and enrichment: `int_orders_enriched`, `int_seller_metrics`
- **Marts** — analytics-ready tables: `mart_customers`, `mart_orders`, `mart_revenue`, `mart_sellers`

## Development

```bash
uv sync
make seed        # load Olist data into PostgreSQL
make dbt-run     # run dbt models
make dbt-test    # run dbt tests
make run         # start FastAPI
make docker-up   # full stack via Docker Compose
```

## Roadmap

- [x] FastAPI skeleton, structured logging, Docker Compose
- [ ] Step 1 — Data Foundation: PostgreSQL + Olist seed
- [ ] Step 2 — dbt Modeling: staging → intermediate → mart, schema.yml
- [ ] Step 3 — Query Engine: SQL executor, manifest parser, SQL validator
- [ ] Step 4 — LangGraph Workflow: 6-node graph with retry loop
- [ ] Step 5 — FastAPI Endpoints: /query, /schema, /history
- [ ] Step 6 — Redis Cache
- [ ] Step 7 — Streamlit UI + Langfuse + portfolio polish
