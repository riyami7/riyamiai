"""User-related schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr = Field(
        ...,
        example="user@example.com",
        description="User's email address"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        example="John Doe",
        description="User's full name"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active"
    )


class UserCreate(UserBase):
    """Schema for creating a new user (admin-only endpoint)."""
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        example="securepassword123",
        description="User's password (min 8 characters)"
    )
    role: UserRole = Field(
        default=UserRole.USER,
        description="User's role (admin or user)"
    )
    system_prompt: str = Field(
        default="You are a helpful assistant.",
        description="System prompt used for LLM interactions"
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing user. All fields are optional."""
    email: Optional[EmailStr] = Field(
        default=None,
        example="user@example.com",
        description="User's email address"
    )
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        example="John Doe",
        description="User's full name"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Whether the user account is active"
    )
    role: Optional[UserRole] = Field(
        default=None,
        description="User's role (admin or user)"
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt used for LLM interactions"
    )


class UserResponse(UserBase):
    """Schema for user response with additional fields."""
    id: int = Field(
        ...,
        example=1,
        description="Unique user identifier"
    )
    role: UserRole = Field(
        ...,
        description="User's role"
    )
    system_prompt: str = Field(
        ...,
        description="System prompt used for LLM interactions"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the user was created"
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the user was last updated"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "name": "John Doe",
                "role": "user",
                "is_active": True,
                "system_prompt": "You are a helpful assistant.",
                "created_at": "2026-02-10T12:00:00Z",
                "updated_at": "2026-02-10T12:00:00Z"
            }
        }
    }


class UserListResponse(BaseModel):
    """Schema for listing users with pagination info."""
    users: list[UserResponse] = Field(
        ...,
        description="List of users"
    )
    total: int = Field(
        ...,
        example=10,
        description="Total number of users"
    )
