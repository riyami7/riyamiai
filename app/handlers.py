"""Global exception handlers."""

import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import AppException
from app.schemas.error import ErrorResponse, ValidationErrorResponse, ValidationErrorDetail
from app.config import get_settings

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(
        f"AppException: {exc.error_code} - {exc.detail}",
        extra={"path": request.url.path, "context": exc.context}
    )

    error_response = ErrorResponse(
        error_code=exc.error_code,
        detail=exc.detail,
        path=request.url.path,
        timestamp=datetime.utcnow(),
        context=exc.context if get_settings().debug else None,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json", exclude_none=True),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append(
            ValidationErrorDetail(
                field=field or "body",
                message=error["msg"],
                type=error["type"],
            )
        )

    logger.warning(
        f"Validation error on {request.url.path}",
        extra={"errors": [e.model_dump() for e in errors]}
    )

    error_response = ValidationErrorResponse(
        error_code="VALIDATION_ERROR",
        detail="Request validation failed",
        path=request.url.path,
        timestamp=datetime.utcnow(),
        errors=errors,
    )

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(mode="json", exclude_none=True),
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    logger.error(
        f"Database error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True,
    )

    # Don't expose database details in production
    detail = "A database error occurred"
    if get_settings().debug:
        detail = f"Database error: {str(exc)}"

    error_response = ErrorResponse(
        error_code="DATABASE_ERROR",
        detail=detail,
        path=request.url.path,
        timestamp=datetime.utcnow(),
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode="json", exclude_none=True),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True,
    )

    # Don't expose internal details in production
    detail = "An unexpected error occurred"
    if get_settings().debug:
        detail = f"Internal error: {str(exc)}"

    error_response = ErrorResponse(
        error_code="INTERNAL_ERROR",
        detail=detail,
        path=request.url.path,
        timestamp=datetime.utcnow(),
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode="json", exclude_none=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
