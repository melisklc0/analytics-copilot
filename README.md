# Analytics Copilot

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-FF6B35?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![dbt](https://img.shields.io/badge/dbt-1.9+-FF694B?style=flat-square&logo=dbt&logoColor=white)](https://getdbt.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Apache Superset](https://img.shields.io/badge/Superset-BI-20A7C9?style=flat-square&logo=apache-superset&logoColor=white)](https://superset.apache.org)
[![Langfuse](https://img.shields.io/badge/Langfuse-Traced-7B2FBE?style=flat-square)](https://langfuse.com)

> **Natural language interface for dbt-modeled PostgreSQL data warehouses.**  
> Ask a question in plain English. Get back validated SQL, query results, and a natural-language explanation — no aggregation in the AI layer, no hallucinated column names.


## The Core Idea

Most NL2SQL systems hand the LLM a raw schema and hope it writes correct GROUP BY logic. This one doesn't.

**dbt aggregates. The AI only queries.**

All GROUP BY, JOIN, SUM, COUNT, and AVG logic lives in dbt mart models — pre-computed, tested, and documented. The AI generates only `SELECT ... FROM mart.* WHERE ... ORDER BY ... LIMIT ...` queries. When a question arrives, the answer is already in the mart table; the LLM just needs to filter it correctly.

```sql
-- What the LLM is NOT allowed to generate
SELECT customer_id, SUM(payment_value) AS clv
FROM raw.orders
GROUP BY 1

-- What it generates instead
SELECT customer_id, customer_lifetime_value
FROM mart_customers
ORDER BY customer_lifetime_value DESC
LIMIT 10
```

This constraint keeps the SQL validator simple, makes hallucinated aggregations structurally impossible, and makes the value of data modeling visible — without the mart tables, the AI cannot answer.

LLM context comes from `dbt docs generate` rather than raw `INFORMATION_SCHEMA`. The manifest includes human-written column descriptions, test definitions, and `meta.filterable` hints — the AI only sees columns that are documented and tested.


## Architecture

```
User question (natural language)
        │
        ▼
┌─────────────────────────────────────────┐
│          FastAPI Gateway                │
│  POST /query · GET /schema · /health   │
│  structured JSON logging · request-ID  │
└────────────────┬────────────────────────┘
                 │
                 ▼
       ┌──────────────────┐
       │   Redis Cache    │  ← normalized question hash
       │   (TTL: 1 hour)  │  ← cache hit → skip LLM entirely
       └────────┬─────────┘
                │ miss
                ▼
┌────────────────────────────────────────────────┐
│              LangGraph Workflow                │
│                                                │
│  [Intent Classifier]                           │
│          ↓                                     │
│  [Schema Selector]  ←── dbt manifest.json      │
│          ↓           (curated schema context)  │
│  [SQL Generator]    ←── LangChain prompt       │
│          ↓                                     │
│  [SQL Validator]    ←── 3-layer validation     │
│       ↙      ↘                                 │
│    valid   invalid ──→ retry (max 2)           │
│       ↓                                        │
│  [SQL Executor]     ←── analyst_ro role        │
│          ↓           (read-only, 500 row cap)  │
│  [Result Formatter] ──→ SQL + rows + NL text   │
└────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────┐
│              PostgreSQL                        │
│  raw schema (Olist) · dbt marts               │
│  analyst_ro: SELECT only · no DDL/DML         │
└────────────────────────────────────────────────┘
```


## Three Layers, One Platform

| | dbt | Apache Superset | AI Copilot |
|---|---|---|---|
| **Role** | Data foundation | Business intelligence | Natural language interface |
| **Consumers** | BI + AI layers | Business users | Anyone |
| **Output** | Tested mart tables | Dashboards & charts | SQL + query results |
| **Key constraint** | Single source of truth for all metrics | Read-only `superset_ro` role | Cannot aggregate — queries dbt marts only |

dbt is the heart. Both the BI layer and the AI layer consume the same mart models — metric definitions live in one place, tested once.


## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13+, FastAPI, Uvicorn, psycopg (async) |
| AI Workflow | LangGraph, LangChain, OpenAI API |
| Data Modeling | dbt Core 1.9+, dbt-postgres |
| SQL Validation | sqlglot (AST-level parsing) |
| Database | PostgreSQL 17 |
| Cache | Redis |
| Observability | Langfuse, structured JSON logging |
| BI | Apache Superset (dashboard mart layer) |
| Infra | Docker Compose, uv, multi-stage Dockerfile |
| UI | Streamlit |
| Quality | mypy (strict), ruff, pytest |


## Data Modeling (dbt)

The warehouse runs on the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 100k+ orders, 9 source tables, open license.

```
data/raw/ (Olist CSVs)
        │
        ▼
models/staging/              ← type casting, column renaming, 1:1 with sources
        │
        ▼
models/intermediate/         ← join orchestration, business logic
        │
        ▼
models/marts/
    ├── ai/                  ← consumed by the AI copilot (tagged [ai, mart])
    │   ├── mart_customers.sql          (1 row/customer: LTV, segment, avg review)
    │   ├── mart_orders.sql             (1 row/order: revenue, delivery days, payment type)
    │   ├── mart_sellers.sql            (1 row/seller: orders, revenue, on-time %)
    │   ├── mart_product_categories.sql
    │   ├── mart_monthly_revenue_by_category.sql
    │   └── mart_payment_behavior.sql
    ├── core/                ← fact/dimension tables for analysts
    └── dashboard/           ← pre-aggregated reports for Superset
```

Every model has a `schema.yml` with column descriptions, `not_null`/`unique` tests, and `meta.filterable` hints that flow directly into the LLM prompt context.


## Business Intelligence (Superset)

Superset connects to PostgreSQL via a dedicated `superset_ro` read-only role and queries the `dashboard` mart subdirectory — pre-aggregated tables purpose-built for chart performance.

The separation from the AI marts is intentional: dashboard marts are denormalized for fast GROUP BY at query time in Superset, while AI marts are denormalized so the AI never needs to GROUP BY at all. Same dbt foundation, different mart shapes for different consumers.

`superset_ro` has SELECT access on `main_marts` only — no raw schema, no intermediate models, no DDL.


## AI Interface (NL2SQL)

Natural language questions flow through a LangGraph workflow: intent classification → schema selection from dbt manifest → SQL generation → validation → execution → result formatting. The LangGraph retry loop feeds validation errors back to the SQL generator (max 2 retries) before returning a graceful error.

### SQL Validation (3-Layer Defense)

The validator runs before any query reaches PostgreSQL, using sqlglot to parse SQL into an AST — string matching is not used.

| Layer | What it checks |
|---|---|
| **Write guard** | Rejects anything that isn't a `SELECT`. INSERT, UPDATE, DELETE, DDL → rejected. |
| **Aggregation guard** | Rejects GROUP BY, JOIN, SUM, COUNT, AVG at the AST node level. |
| **Schema check** | Validates table and column references against the dbt manifest. |

On failure, a structured error message feeds back to the SQL generator node (max 2 retries before graceful error).


## Security Model

- **Read-only PostgreSQL role** (`analyst_ro`): even if the validator is bypassed, PostgreSQL rejects writes at the role level
- **Schema-based access control**: `analyst_ro` has SELECT on `main_marts` and `main_staging` only; raw schema is not exposed
- **Row cap + timeout**: 500-row LIMIT applied automatically; 10-second statement timeout enforced via connection option
- **Secret handling**: credentials stored as `pydantic.SecretStr`, never logged


## Observability

Every workflow run is traced in [Langfuse](https://langfuse.com/) — LLM calls, token usage, latency, SQL generated, validation outcome, cache hit/miss. Structured JSON logs include request-ID correlation.

```json
{
  "timestamp": "2025-01-15T10:23:41.123Z",
  "level": "INFO",
  "message": "sql_validator: passed",
  "request_id": "req-abc123",
  "model": "mart_customers",
  "elapsed_ms": 12
}
```


## Project Status

| Phase | Status | Description |
|---|---|---|
| Data Foundation | ✅ Done | PostgreSQL 17, Olist seed, `analyst_ro` role |
| dbt Modeling | ✅ Done | 14 models across staging → intermediate → marts |
| Query Engine | ✅ Done | SQL executor, manifest parser, 3-layer validator |
| LangGraph Workflow | 🔨 In Progress | Intent classifier, schema selector, SQL generator, retry loop |
| FastAPI Endpoints | ⏳ Upcoming | `POST /query`, `GET /schema`, `GET /history` |
| Redis Cache | ⏳ Upcoming | Query hash cache, TTL 1 hour |
| Streamlit UI + Polish | ⏳ Upcoming | Demo interface, `make demo` one-command setup |


## Quick Start

**Prerequisites:** Docker, uv

```bash
git clone https://github.com/melisklc0/analytics-copilot
cd analytics-copilot

cp .env.example .env          # add your OpenAI API key

make docker-up                # PostgreSQL + API + optional Langfuse/Superset

# Download the Olist dataset from Kaggle and place CSVs under data/raw/
# https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

make seed                     # load Olist data into PostgreSQL
make dbt-pipeline             # deps → run → test → docs generate

make run                      # FastAPI on :8090 with hot reload
make test                     # pytest
```

```bash
curl http://localhost:8090/health
# {"status": "ok", "service": "analytics-copilot-api"}
```

**Local development:**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/analytics_copilot/
uv run pytest
```

CI runs all four gates on every push to `main` and every PR.


## Repository Structure

```
src/analytics_copilot/
├── app.py                    # FastAPI factory + lifespan manager
├── api/                      # Routers, exception handlers
├── core/                     # Pydantic Settings, custom exceptions
├── observability/            # Structured JSON logging, Langfuse integration
├── schemas/                  # Pydantic API contracts
├── services/
│   ├── manifest_parser.py    # dbt manifest.json → LLM schema context
│   ├── sql_validator.py      # 3-layer AST-based SQL validation
│   └── sql_executor.py       # Async PostgreSQL executor (read-only)
└── workflow/                 # LangGraph graph + nodes

dbt/
├── models/staging/           # 7 source-aligned views
├── models/intermediate/      # 2 business-logic views
└── models/marts/             # 14 analytics-ready tables (ai / core / dashboard)

infra/
├── postgres/init.sql         # Schema DDL + role-based access control
├── api/Dockerfile            # Multi-stage build, non-root user
└── langfuse/                 # Self-hosted LLM observability

tests/
├── unit/services/            # SQL validator, executor, manifest parser
└── test_documents.py         # Document upload/CRUD integration tests
```


## License

Apache 2.0
