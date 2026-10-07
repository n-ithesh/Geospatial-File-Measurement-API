"""Custom exception classes and FastAPI exception handlers.

Each exception maps to a specific HTTP status code and returns a
JSON body of the form ``{"detail": "<message>"}``.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------


class AppError(Exception):
    """Base class for all application-level errors."""

    status_code: int = 500
    default_detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class InvalidFileError(AppError):
    """Raised when a file is structurally invalid (e.g. corrupt zip, bad geometry)."""

    status_code = 422
    default_detail = "The uploaded file is invalid."


class FileTooLargeError(AppError):
    """Raised when a file exceeds the configured size limit."""

    status_code = 413
    default_detail = "The uploaded file exceeds the maximum allowed size."


class UnsupportedExtensionError(AppError):
    """Raised when the file extension is not in the allowed set."""

    status_code = 400
    default_detail = "Unsupported file extension."


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    default_detail = "The requested resource was not found."


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def _make_response(exc: AppError) -> JSONResponse:
    """Build a consistent JSON error response from an AppError."""
    logger.warning(
        "Application error [%s %d]: %s",
        type(exc).__name__,
        exc.status_code,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Generic handler for all AppError subclasses."""
    return _make_response(exc)


async def invalid_file_handler(request: Request, exc: InvalidFileError) -> JSONResponse:
    return _make_response(exc)


async def file_too_large_handler(
    request: Request, exc: FileTooLargeError
) -> JSONResponse:
    return _make_response(exc)


async def unsupported_extension_handler(
    request: Request, exc: UnsupportedExtensionError
) -> JSONResponse:
    return _make_response(exc)


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return _make_response(exc)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to the FastAPI application."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(InvalidFileError, invalid_file_handler)  # type: ignore[arg-type]
    app.add_exception_handler(FileTooLargeError, file_too_large_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UnsupportedExtensionError, unsupported_extension_handler)  # type: ignore[arg-type]
    app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
