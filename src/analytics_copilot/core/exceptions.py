class ApplicationError(Exception):
    """Base exception for OpenRAG Eval application errors."""

    code = "application_error"
    status_code = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class SQLGenerationError(ApplicationError):
    """Raised when the LLM fails to produce a SQL query."""

    code = "sql_generation_error"
    status_code = 500


class SQLValidationError(ApplicationError):
    """Raised when generated SQL fails validation checks."""

    code = "sql_validation_error"
    status_code = 422


class SQLExecutionError(ApplicationError):
    """Raised when PostgreSQL rejects or fails to execute a query."""

    code = "sql_execution_error"
    status_code = 500


class ConfigurationError(ApplicationError):
    """Raised when the application is misconfigured at startup."""

    code = "configuration_error"
    status_code = 500


class QueryTimeoutError(ApplicationError):
    """Raised when a query exceeds the statement timeout limit."""

    code = "query_timeout"
    status_code = 504

    def __init__(self, timeout_ms: int) -> None:
        super().__init__(f"Query exceeded the {timeout_ms // 1000}s timeout limit")


class SupersetEmbedError(ApplicationError):
    """Raised when Superset cannot mint a guest token (unreachable or rejected)."""

    code = "superset_embed_error"
    status_code = 502
