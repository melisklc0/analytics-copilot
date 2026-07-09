# AGENTS.md

You are working on Analytics Copilot: a natural-language analytics interface over a dbt-modeled PostgreSQL warehouse.

## How to Work

- Do not jump straight into implementation.
- First inspect relevant files and existing patterns.
- For non-trivial changes, explain the finding, root cause, proposed fix, and files to touch; then wait for approval.
- If the user clearly says “implement”, “fix it”, or “go ahead”, proceed after a short plan.
- Do not ask the user to run commands if you can safely run them yourself.
- Use available tools for repo search, file inspection, and checks.
- Prefer `rg` for search.
- Keep changes small and scoped.

## Before Changing Common Areas

- Exceptions: inspect `core/exceptions.py` and `api/exception_handlers.py`.
- Logging: inspect `observability/logger.py`, `observability/logging_config.json`, and nearby logger usage. No `print`.
- Config: inspect `core/config.py`; update `.env.example` and docs if needed.
- Endpoints: inspect existing routers, schemas, dependencies, and endpoint tests.
- Workflow nodes: inspect `workflow/graph.py`, `workflow/state.py`, existing nodes, and workflow tests.
- Prompts: keep templates in `prompts/*.yaml`; never hardcode prompt text in Python.
- dbt: respect model grain; if the needed grain/metric is missing, propose a mart change instead of patching around it.

## Critical Domain Rules

- Runtime SQL may only query dbt AI mart tables.
- Runtime SQL must be simple: `SELECT ... FROM ... WHERE ... ORDER BY ... LIMIT ...`.
- Runtime SQL must not contain `JOIN`, `GROUP BY`, aggregates, window functions, CTEs, subqueries, writes, or DDL.
- The AI layer does not aggregate, join, or compute business metrics.
- All business metrics, joins, aggregations, and grain decisions belong in dbt marts.
- If an answer needs missing aggregation, dimension, or grain, fail gracefully or suggest a new mart.

## Quality Rules

- Follow existing project patterns; avoid wrapper hacks.
- Do not add dependencies without asking.
- Do not edit `uv.lock` manually.
- Do not remove or loosen tests to hide failures.
- Every new endpoint, service, node, validator, or public behavior needs tests.
- Mock LLM, PostgreSQL, Redis, Langfuse, and network calls in unit tests.
- Keep comments, docstrings, prompts, and technical text in English.

## Checks

Run relevant checks after changes when possible:

```bash
uv run ruff format
uv run mypy src/analytics_copilot/
uv run pytest
```

## References

Read when relevant:

docs/VIZYON.md
docs/dbt-architecture.md
docs/workflow-design.md