"""System routes for health checks and configuration."""

from fastapi import APIRouter, Depends
from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.schemas.health import HealthResponse, HealthStatus
from app.schemas.system import SystemInfoResponse, ConfigResponse

router = APIRouter(
    prefix="/system",
    tags=["System"]
)


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Check the health status of the API."""
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        version=settings.app_version,
        environment=settings.env,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/info", response_model=SystemInfoResponse)
async def system_info() -> SystemInfoResponse:
    """Get system information including Python and FastAPI versions."""
    return SystemInfoResponse(
        python_version="3.11.2",
        fastapi_version="0.115.6"
    )


@router.get("/config", response_model=ConfigResponse)
async def get_config(settings: Settings = Depends(get_settings)) -> ConfigResponse:
    """Get non-sensitive application configuration."""
    return ConfigResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.env,
        debug=settings.debug
    )
