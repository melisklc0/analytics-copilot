from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from analytics_copilot.core.exceptions import ApplicationError
from analytics_copilot.schemas.common import ErrorResponse


def register_exception_handlers(app: FastAPI) -> None:
    """Register HTTP exception handlers for application errors."""

    @app.exception_handler(ApplicationError)
    async def handle_application_error(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        payload = ErrorResponse(code=exc.code, message=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(),
        )
