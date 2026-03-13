"""Health check schemas."""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Possible health status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthResponse(BaseModel):
    """Health check response model."""
    status: HealthStatus = Field(
        ...,
        description="Current health status of the service"
    )
    version: str = Field(
        ...,
        example="0.1.0",
        description="API version"
    )
    environment: str = Field(
        ...,
        example="production",
        description="Deployment environment"
    )
    timestamp: datetime = Field(
        ...,
        description="UTC timestamp of the health check"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "environment": "development",
                "timestamp": "2026-02-10T12:00:00Z"
            }
        }
    }
