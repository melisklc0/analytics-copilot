.PHONY: test run seed dbt-run dbt-test dbt-docs docker-build docker-up docker-postgres

test:
	uv run pytest

run:
	uv run uvicorn analytics_copilot.app:app --app-dir src --host 0.0.0.0 --port 8090 --reload

seed:
	uv run python scripts/load_olist.py

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
