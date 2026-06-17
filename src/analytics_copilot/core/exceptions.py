class ApplicationError(Exception):
    """Base exception for OpenRAG Eval application errors."""

    code = "application_error"
    status_code = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DocumentNotFoundError(ApplicationError):
    """Raised when a requested document does not exist."""

    code = "document_not_found"
    status_code = 404

    def __init__(self) -> None:
        super().__init__("Document not found")


class UnsupportedDocumentFormatError(ApplicationError):
    """Raised when an uploaded document format is not supported."""

    code = "unsupported_document_format"
    status_code = 415

    def __init__(self) -> None:
        super().__init__("Unsupported document format")


class DocumentTextExtractionError(ApplicationError):
    """Raised when text cannot be extracted from an uploaded document."""

    code = "document_text_extraction_failed"
    status_code = 400

    def __init__(self, message: str = "Could not extract text from document") -> None:
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


class QueryTimeoutError(ApplicationError):
    """Raised when a query exceeds the statement timeout limit."""

    code = "query_timeout"
    status_code = 504

    def __init__(self, timeout_ms: int) -> None:
        super().__init__(f"Query exceeded the {timeout_ms // 1000}s timeout limit")
