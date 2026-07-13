.PHONY: test run seed dbt-pipeline dbt-run dbt-test dbt-docs docker-build docker-up docker-postgres \
	up up-dashboard up-observability up-all down down-volumes

test:
	uv run pytest

run:
	uv run uvicorn analytics_copilot.app:app --app-dir src --host 0.0.0.0 --port 8090 --reload

seed:
	uv run python scripts/load_olist.py

dbt-pipeline:
	cd dbt && uv run dbt deps && uv run dbt run && uv run dbt test && uv run dbt docs generate

dbt-run:
	cd dbt && uv run dbt run

dbt-test:
	cd dbt && uv run dbt test

dbt-docs:
	cd dbt && uv run dbt docs generate

docker-build:
	docker compose build analytics-copilot-api

docker-postgres:
	docker compose up postgres -d

docker-up:
	docker compose up analytics-copilot-api

# ── Docker stacks (profiles) ────────────────────────────────────────────────
# Core (Postgres → seed sample → dbt build → API) always starts; profiles add
# heavier optional stacks on top. Enabling a profile from nothing still brings
# core up too, since core services carry no profile.

up:                      ## core only: postgres + seed + dbt + api
	docker compose up -d

up-dashboard:            ## core + Superset BI (:8088)
	docker compose --profile dashboard up -d

up-observability:        ## core + Langfuse tracing (:3000)
	docker compose --profile observability up -d

up-all:                  ## core + Superset + Langfuse
	docker compose --profile dashboard --profile observability up -d

down:                    ## stop & remove all containers (incl. profiled), keep data
	docker compose --profile dashboard --profile observability down

down-volumes:            ## stop & remove everything incl. volumes (wipes seeded data)
	docker compose --profile dashboard --profile observability down -v
