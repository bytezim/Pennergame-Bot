"""
Centralized error handling for FastAPI endpoints.

Provides consistent error responses and logging.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from .logging_config import get_logger

logger = get_logger(__name__)


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class InputValidationError(APIError):
    """Raised when input validation fails (API level)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class NotFoundError(APIError):
    """Raised when resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(APIError):
    """Raised when there's a conflict with current state."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions."""
    logger.error(
        f"API Error: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.message,
            "details": exc.details,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException from FastAPI."""
    logger.warning(
        f"HTTP Exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True,
        extra={"path": request.url.path},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc) if logger.level <= 10 else None,  # Show in debug mode
        },
    )


def register_error_handlers(app):
    """Register all error handlers with FastAPI app."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
