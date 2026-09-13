class AppError(Exception):
    """Base class for expected application failures."""

    status_code = 500
    error_code = "application_error"


class LLMParseError(AppError):
    """Raised when an LLM response cannot satisfy the expected JSON contract."""

    status_code = 502
    error_code = "llm_parse_error"


class DatabaseUnavailableError(AppError):
    """Raised when the application cannot reach its SQLite database."""

    status_code = 503
    error_code = "database_unavailable"
