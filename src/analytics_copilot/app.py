from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from analytics_copilot.api.exception_handlers import register_exception_handlers
from analytics_copilot.api.middleware import RequestIDMiddleware
from analytics_copilot.api.router import api_router
from analytics_copilot.core.config import get_settings
from analytics_copilot.observability.logger import setup_logging
from analytics_copilot.observability.tracing import flush_langfuse, get_langfuse
from analytics_copilot.workflow.graph import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    get_langfuse()
    app.state.graph = build_graph()
    yield
    flush_langfuse()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging()

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        lifespan=lifespan,
    )
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
