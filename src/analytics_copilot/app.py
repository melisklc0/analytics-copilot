from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from analytics_copilot.api.exception_handlers import register_exception_handlers
from analytics_copilot.api.router import api_router
from analytics_copilot.core.config import get_settings
from analytics_copilot.observability.logger import setup_logging
from analytics_copilot.observability.tracing import flush_langfuse, get_langfuse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    get_langfuse()  # initialize on startup — logs tracing status
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
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
