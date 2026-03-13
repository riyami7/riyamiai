"""Authentication-related schemas."""

from pydantic import BaseModel, Field, EmailStr


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr = Field(
        ...,
        example="user@example.com",
        description="User's email address"
    )
    password: str = Field(
        ...,
        min_length=1,
        example="securepassword123",
        description="User's password"
    )


class TokenResponse(BaseModel):
    """Schema for token response after successful login."""
    access_token: str = Field(
        ...,
        description="JWT access token"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }
    }
