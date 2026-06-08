from fastapi import FastAPI

from analytics_copilot.api.exception_handlers import register_exception_handlers
from analytics_copilot.api.router import api_router
from analytics_copilot.core.config import get_settings
from analytics_copilot.observability.logger import setup_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging()

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
