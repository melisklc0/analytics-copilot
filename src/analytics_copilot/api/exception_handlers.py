import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from analytics_copilot.core.exceptions import ApplicationError
from analytics_copilot.schemas.common import ErrorResponse

log = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        log.error(
            "application error",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=exc.status_code >= 500,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(code=exc.code, message=exc.message).model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        log.exception(
            "unexpected error",
            extra={"path": request.url.path, "method": request.method},
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                code="internal_error", message="An unexpected error occurred."
            ).model_dump(),
        )
