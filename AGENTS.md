# AGENTS.md

You are working on **Analytics Copilot**: a natural language analytics interface over a dbt-modeled PostgreSQL data warehouse.

The system translates plain-English questions into validated SQL queries against dbt mart tables and returns structured results. The AI layer does not aggregate, join, or compute — dbt handles all of that in mart models. The AI generates `SELECT ... FROM mart.* WHERE ... ORDER BY ... LIMIT ...` queries only.

Target vision and roadmap: `docs/VIZYON.md`.

## Scope

- Main code: `src/analytics_copilot/`
- Tests: `tests/`
- dbt project: `dbt/`
- Data: `data/raw/` (CSV seeds, git-ignored), `data/processed/`
- Scripts: `scripts/`
- Infra: `infra/`, `docker-compose.yml`, `Makefile`
- Docs: `docs/`

## Stack

- Python 3.13+
- FastAPI, Uvicorn
- Pydantic / pydantic-settings
- pytest, uv
- dbt Core, dbt-postgres
- PostgreSQL (`psycopg`)
- Planned: LangGraph, LangChain, OpenAI API, Redis, Langfuse, Streamlit

## Commands

```bash
uv sync
make seed         # load Olist raw data into PostgreSQL
make dbt-run      # dbt run
make dbt-test     # dbt test
make dbt-docs     # dbt docs generate
make run          # uvicorn dev server
make test         # pytest
make docker-up    # full stack
```

Direct:

```bash
uv run pytest
uv run uvicorn analytics_copilot.app:app --app-dir src --host 0.0.0.0 --port 8090 --reload
docker compose up analytics-copilot-api
```

## Docker Note

Docker runs inside WSL on this machine. Use WSL-aware paths and Docker context when troubleshooting.

## Project Shape

```text
src/analytics_copilot/
+-- app.py
+-- api/
+-- core/
+-- observability/
+-- schemas/
+-- services/
+-- workflow/        ← LangGraph graph, nodes, state (Step 4)

dbt/
+-- dbt_project.yml
+-- profiles.yml
+-- models/
    +-- staging/
    +-- intermediate/
    +-- marts/

scripts/
+-- seed_raw.py      ← load Olist CSVs into PostgreSQL raw schema
```

## Key Design Rules

- **AI does not aggregate.** All GROUP BY, SUM, COUNT, AVG, JOIN logic lives in dbt mart models. The SQL generator produces only simple SELECT queries against mart tables.
- **LLM context comes from dbt manifest.json.** Never pass raw schema introspection to the LLM — use `dbt docs generate` output so column descriptions and tests are included.
- **SQL validator enforces the aggregation guard.** Reject any generated SQL containing `GROUP BY`, `SUM(`, `COUNT(`, `AVG(`, `JOIN` — retry with error message.
- **analyst_ro role is mandatory.** The SQL executor connects via a read-only PostgreSQL role. The LLM cannot issue INSERT, UPDATE, DELETE, or DDL.

## Roadmap Status

- Done: FastAPI skeleton, exception handling, structured logging, Docker Compose, basic tests
- Step 1 (next): Data Foundation — PostgreSQL + Olist seed
- Step 2: dbt Modeling — staging → intermediate → mart, schema.yml
- Step 3: Query Engine — SQL executor, manifest parser, SQL validator
- Step 4: LangGraph Workflow — intent classifier, schema selector, SQL generator, validator, executor, formatter
- Step 5: FastAPI Endpoints — /query, /schema, /history
- Step 6: Redis Cache
- Step 7: UI + Observability + Polish

## Rules

- Search before adding new files, schemas, services, config keys, prompts, or endpoints.
- Follow existing repo structure.
- Use type hints on public code.
- Prefer async patterns for API/service code.
- Keep comments, docstrings, and prompts in English.
- Keep prompt templates in `prompts/` YAML files — never hardcode in Python.
- Mock LLM, PostgreSQL, Redis, Langfuse, and network calls in unit tests.
- Update `.env.example` and docs when adding required config.

## Boundaries

Ask first before:

- Adding dependencies.
- Changing public API contracts.
- Adding a new top-level package, database, worker, or frontend framework.
- Large dependency or version migrations.

Never:

- Commit secrets or private data.
- Edit `uv.lock` manually.
- Remove or loosen tests to hide failures.
- Use private company data as sample data.
- Hardcode prompts in Python.
- Let the AI layer run aggregation queries — that belongs in dbt.
- Connect to PostgreSQL with a role that has write access.

## Commits

Use conventional commits:

```text
feat(dbt): add mart_customers model with CLV calculation
feat(workflow): add sql-validator node with aggregation guard
feat(api): add POST /query endpoint
fix(executor): enforce row limit on all queries
test(validator): cover aggregation guard rejection cases
docs(vizyon): update roadmap status
```
