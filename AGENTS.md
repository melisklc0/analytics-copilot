# AGENTS.md

You are working on **OpenRAG Eval Platform**: a Python/FastAPI backend for RAG, retrieval evaluation, and observability over developer documentation.

## Scope

- Main code: `src/openrag_eval/`
- Tests: `tests/`
- Infra: `infra/`, `docker-compose.yml`, `Makefile`
- Planning docs: `docs/project-plan.md`, `docs/folder-structure.md`
- Default domain: public developer docs and synthetic technical docs.

## Stack

- Python 3.13+
- FastAPI, Uvicorn
- Pydantic / pydantic-settings
- pytest
- uv
- Planned: Qdrant, OpenAI, LangGraph, PostgreSQL, Alembic, Langfuse

## Commands

Run from repo root:

```bash
uv sync
make run
make test
make docker-up
```

Direct commands:

```bash
uv run pytest
uv run uvicorn openrag_eval.app:app --app-dir src --host 0.0.0.0 --port 8090 --reload
docker compose up openrag-eval-api
```

## Docker Note

Docker runs inside WSL on this machine. Use WSL-aware paths and Docker context when troubleshooting Docker/Compose issues.

## Project Shape

```text
src/openrag_eval/
+-- app.py
+-- api/
+-- core/
+-- observability/
+-- schemas/
+-- clients/
+-- services/
```

Keep API routers thin. Put business logic in `services/`. Put external integrations in `clients/`. Put request/response models in `schemas/`.

## RAG Roadmap

- Ingestion: load docs, chunk, embed, index.
- Retrieval: Qdrant search, BM25, hybrid scoring, filters, reranking.
- Workflow: LangGraph query rewrite, retrieve, rerank, answer, citation check.
- Evaluation: precision@k, groundedness, answer relevance, citation correctness.
- Observability: structured logs, traces, latency, tokens, cost, eval scores.

## Rules

- Search before adding new files, schemas, services, config keys, prompts, or endpoints.
- Follow existing repo structure.
- Use type hints on public code.
- Prefer async patterns for API/service code.
- Keep comments and docstrings in English.
- Keep prompts and judge rubrics in config files, not hardcoded in service code.
- Mock external LLM/Qdrant/Langfuse/network calls in unit tests.
- Update `.env.example` and docs when adding required config.
- Prefer project-aware tools before terminal commands for file work.

## Boundaries

Ask first before:

- Adding dependencies.
- Changing public API contracts.
- Adding a new top-level package, database, worker, or frontend framework.
- Large dependency/version migrations.

Never:

- Commit secrets or private data.
- Edit `uv.lock` manually.
- Remove/loosen tests to hide failures.
- Use private company data as sample RAG/eval data.
- Hardcode large prompts in Python.

## Commits

Use conventional commits:

```text
feat(api): add retrieval debug endpoint
feat(ingestion): index markdown documents
fix(config): read qdrant collection from env
test(evaluation): cover judge parsing
docs(architecture): update rag workflow
```
