# syntax=docker/dockerfile:1.7

# ==========================================
# Builder Stage (shared by all images)
# ==========================================
# Dependencies are installed exactly once here; every runtime image below
# copies the resulting venv instead of running `uv sync` again.
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Build-time only: needed to compile wheels that have no prebuilt binary.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency metadata before application code to preserve Docker layer cache.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./

# Layer 1: main runtime deps (API). Cached on every non-ui dep change.
RUN --mount=type=cache,target=/root/.cache \
    uv sync \
    --locked \
    --no-dev \
    --no-install-project

# Layer 2: UI group (streamlit/pandas/requests). Separate layer so main-dep
# changes above do not invalidate this cache. The console shares one venv with
# the API (mirrors agentic-rag), so both targets copy the same /app/.venv.
RUN --mount=type=cache,target=/root/.cache \
    uv sync \
    --locked \
    --no-dev \
    --group ui \
    --no-install-project

# ==========================================
# Runtime Base (shared by api + ui)
# ==========================================
FROM python:3.13-slim AS runtime-base

WORKDIR /app

# Runtime uses a non-root user.
RUN useradd --create-home --shell /usr/sbin/nologin app

# Copy the prebuilt venv with the final runtime owner.
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Ensure runtime entrypoints like python/uvicorn/streamlit stay executable.
RUN find /app/.venv/bin -type f -exec chmod 755 {} +

# ==========================================
# API image
# ==========================================
FROM runtime-base AS api

# Application code (also bind-mounted in development via compose).
COPY --chown=app:app src ./src
COPY --chown=app:app prompts ./prompts

USER app
EXPOSE 8090

# Probe the app from inside the container without adding extra runtime packages.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD /app/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=3)" || exit 1

# Run with the venv interpreter explicitly to avoid PATH/module-resolution surprises.
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "analytics_copilot.app:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8090"]

# ==========================================
# UI image (Streamlit console)
# ==========================================
FROM runtime-base AS ui

# The console is a pure HTTP client — only the Streamlit app, no project package.
COPY --chown=app:app streamlit ./streamlit

USER app
EXPOSE 8501

# Streamlit's built-in health endpoint, probed without extra runtime packages.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD /app/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)" || exit 1

CMD ["/app/.venv/bin/python", "-m", "streamlit", "run", "streamlit/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
