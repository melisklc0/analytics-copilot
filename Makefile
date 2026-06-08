.PHONY: test run docker-build docker-up

test:
	uv run pytest

run:
	uv run uvicorn analytics_copilot.app:app --app-dir src --host 0.0.0.0 --port 8090 --reload

docker-build:
	docker compose build analytics-copilot-api

docker-up:
	docker compose up analytics-copilot-api
