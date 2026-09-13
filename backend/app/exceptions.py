"""Custom exception classes for Lenny Growth Assistant.

These map to standard error codes defined in docs/architecture.md and Checkpoint 3.
"""


class AppError(Exception):
    """Base application exception with standard code and message."""
    def __init__(self, code: str, message: str, status_code: int = 500):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
        }


class SessionNotFoundError(AppError):
    def __init__(self, session_id: str):
        super().__init__(
            code="SESSION_NOT_FOUND",
            message=f"Session '{session_id}' not found.",
            status_code=404,
        )


class ClaudeNotConfiguredError(AppError):
    def __init__(self, message: str = "Anthropic Claude API key is missing or not configured."):
        super().__init__(
            code="CLAUDE_NOT_CONFIGURED",
            message=message,
            status_code=503,
        )


class OllamaUnavailableError(AppError):
    def __init__(self, message: str = "Local Ollama service is unreachable or returned an error."):
        super().__init__(
            code="OLLAMA_UNAVAILABLE",
            message=message,
            status_code=503,
        )


class ModelUnavailableError(AppError):
    def __init__(self, message: str = "Active LLM reasoning provider is unavailable or failed."):
        super().__init__(
            code="MODEL_UNAVAILABLE",
            message=message,
            status_code=503,
        )


class ModelTimeoutError(AppError):
    def __init__(self, message: str = "Reasoning model generation timed out."):
        super().__init__(
            code="MODEL_TIMEOUT",
            message=message,
            status_code=504,
        )


class RetrievalEmptyError(AppError):
    def __init__(self, message: str = "No transcript chunks found in the database corpus."):
        super().__init__(
            code="RETRIEVAL_EMPTY",
            message=message,
            status_code=200,
        )
