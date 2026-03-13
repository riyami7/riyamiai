"""Centralized application exceptions."""

from typing import Any


class AppException(Exception):
    """Base application exception.
    
    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        detail: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        headers: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        self.headers = headers
        self.context = context or {}
        super().__init__(self.detail)


class NotFoundError(AppException):
    """Resource not found exception (404)."""

    def __init__(
        self,
        detail: str = "Resource not found",
        error_code: str = "NOT_FOUND",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            status_code=404,
            error_code=error_code,
            context=context,
        )


class AlreadyExistsError(AppException):
    """Resource already exists exception (409)."""

    def __init__(
        self,
        detail: str = "Resource already exists",
        error_code: str = "ALREADY_EXISTS",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            status_code=409,
            error_code=error_code,
            context=context,
        )


class ValidationError(AppException):
    """Validation error exception (422)."""

    def __init__(
        self,
        detail: str = "Validation error",
        error_code: str = "VALIDATION_ERROR",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            status_code=422,
            error_code=error_code,
            context=context,
        )


class DatabaseError(AppException):
    """Database error exception (500)."""

    def __init__(
        self,
        detail: str = "Database error occurred",
        error_code: str = "DATABASE_ERROR",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            status_code=500,
            error_code=error_code,
            context=context,
        )


class UnauthorizedError(AppException):
    """Unauthorized access exception (401)."""

    def __init__(
        self,
        detail: str = "Unauthorized",
        error_code: str = "UNAUTHORIZED",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            status_code=401,
            error_code=error_code,
            context=context,
        )


class ForbiddenError(AppException):
    """Forbidden access exception (403)."""

    def __init__(
        self,
        detail: str = "Forbidden",
        error_code: str = "FORBIDDEN",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            status_code=403,
            error_code=error_code,
            context=context,
        )


class ServiceUnavailableError(AppException):
    """External service unavailable exception (503)."""

    def __init__(
        self,
        detail: str = "Service unavailable",
        error_code: str = "SERVICE_UNAVAILABLE",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            status_code=503,
            error_code=error_code,
            context=context,
        )
