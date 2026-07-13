# syntax=docker/dockerfile:1.7
#
# Lean dbt runner built from the project's own uv.lock, so the dbt version here
# is byte-for-byte the one used locally (dbt-core 1.11 / dbt-postgres 1.10).
# This keeps package-lock.yml valid across host and container — no version drift.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./

# Install ONLY the dbt group (no API deps, no dev toolchain, no project).
RUN --mount=type=cache,target=/root/.cache \
    uv sync --locked --only-group dbt --no-install-project

# Put the venv's dbt on PATH; the dbt project is bind-mounted at /usr/app.
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /usr/app
