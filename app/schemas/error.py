"""Error response schemas."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized error response schema."""

    error_code: str = Field(
        ...,
        description="Machine-readable error code",
        examples=["NOT_FOUND", "VALIDATION_ERROR"]
    )
    detail: str = Field(
        ...,
        description="Human-readable error message",
        examples=["User not found"]
    )
    path: str | None = Field(
        default=None,
        description="Request path that caused the error",
        examples=["/users/123"]
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the error occurred"
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional context about the error"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "error_code": "NOT_FOUND",
                "detail": "User not found",
                "path": "/users/123",
                "timestamp": "2026-02-11T12:00:00Z",
                "context": {"user_id": 123}
            }
        }
    }


class ValidationErrorDetail(BaseModel):
    """Detail for a single validation error."""

    field: str = Field(
        ...,
        description="Field that failed validation",
        examples=["email"]
    )
    message: str = Field(
        ...,
        description="Validation error message",
        examples=["Invalid email format"]
    )
    type: str = Field(
        ...,
        description="Error type",
        examples=["value_error"]
    )


class ValidationErrorResponse(BaseModel):
    """Validation error response with field details."""

    error_code: str = Field(
        default="VALIDATION_ERROR",
        description="Machine-readable error code"
    )
    detail: str = Field(
        default="Validation error",
        description="Human-readable error message"
    )
    path: str | None = Field(
        default=None,
        description="Request path that caused the error"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the error occurred"
    )
    errors: list[ValidationErrorDetail] = Field(
        ...,
        description="List of validation errors"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "error_code": "VALIDATION_ERROR",
                "detail": "Validation error",
                "path": "/users/",
                "timestamp": "2026-02-11T12:00:00Z",
                "errors": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "type": "value_error"
                    }
                ]
            }
        }
    }
