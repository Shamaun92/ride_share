"""Domain exceptions and a registrar that maps them to HTTP responses.

The service/repository layers raise framework-agnostic exceptions; the API
layer translates them. This keeps business logic free of HTTP concerns.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base class for all domain errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource conflict"


class AuthenticationError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Could not authenticate"


class PermissionDeniedError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Permission denied"


class ValidationError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation failed"


class RateLimitError(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    detail = "Rate limit exceeded"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
