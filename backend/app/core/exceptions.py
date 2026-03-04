"""Custom exception classes and exception handlers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource", identifier: Any = None):
        msg = f"{resource} not found"
        if identifier:
            msg = f"{resource} with id '{identifier}' not found"
        super().__init__(message=msg, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message=message, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class ExternalServiceError(AppException):
    def __init__(self, service: str, message: str = ""):
        msg = f"External service '{service}' error"
        if message:
            msg += f": {message}"
        super().__init__(message=msg, status_code=status.HTTP_502_BAD_GATEWAY)


class LLMServiceUnavailable(AppException):
    def __init__(self, provider: str = "LLM"):
        super().__init__(
            message=f"{provider} service is not configured. Please set the API key.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class VectorStoreUnavailable(AppException):
    def __init__(self):
        super().__init__(
            message="Vector store (Pinecone) is not configured. Please set PINECONE_API_KEY.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# ---- FastAPI exception handlers ----

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle AppException instances."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "details": exc.details,
                "type": type(exc).__name__,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "An internal server error occurred",
                "type": "InternalServerError",
            }
        },
    )
