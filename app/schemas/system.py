"""System-related schemas."""

from pydantic import BaseModel, Field


class SystemInfoResponse(BaseModel):
    """System information response."""
    python_version: str = Field(
        ...,
        example="3.11.2",
        description="Python runtime version"
    )
    fastapi_version: str = Field(
        ...,
        example="0.115.6",
        description="FastAPI framework version"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "python_version": "3.11.2",
                "fastapi_version": "0.115.6"
            }
        }
    }


class ConfigResponse(BaseModel):
    """Configuration response (non-sensitive settings only)."""
    app_name: str = Field(
        ...,
        example="AI Chatbot API",
        description="Application name"
    )
    version: str = Field(
        ...,
        example="0.1.0",
        description="Application version"
    )
    environment: str = Field(
        ...,
        example="development",
        description="Deployment environment"
    )
    debug: bool = Field(
        ...,
        example=False,
        description="Debug mode status"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "app_name": "AI Chatbot API",
                "version": "0.1.0",
                "environment": "development",
                "debug": False
            }
        }
    }


class RootResponse(BaseModel):
    """Root endpoint response."""
    message: str = Field(
        ...,
        example="Welcome to the AI Chatbot API",
        description="Welcome message"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Welcome to the AI Chatbot API"
            }
        }
    }
