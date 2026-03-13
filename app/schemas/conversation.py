"""Conversation-related schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.message import MessageResponse


class ConversationBase(BaseModel):
    """Base conversation schema with common fields."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Conversation title",
        example="Chat about Python",
    )


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""

    model: Optional[str] = Field(
        default=None,
        description="Ollama model name (uses server default if omitted)",
        example="llama3.2",
    )


class ConversationUpdate(BaseModel):
    """Schema for updating an existing conversation. All fields are optional."""

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Conversation title",
        example="Updated conversation title",
    )


class ConversationResponse(BaseModel):
    """Schema for conversation response (list view)."""

    id: int = Field(..., example=1, description="Unique conversation identifier")
    title: str = Field(..., description="Conversation title")
    model: Optional[str] = Field(default=None, description="Ollama model used")
    created_at: datetime = Field(..., description="Timestamp when the conversation was created")
    updated_at: datetime = Field(..., description="Timestamp when the conversation was last updated")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "Chat about Python",
                "model": "llama3.2",
                "created_at": "2026-02-16T12:00:00Z",
                "updated_at": "2026-02-16T12:00:00Z",
            }
        },
    }


class ConversationDetailResponse(ConversationResponse):
    """Schema for conversation response with messages (detail view)."""

    messages: list[MessageResponse] = Field(
        default_factory=list,
        description="List of messages in the conversation",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "Chat about Python",
                "model": "llama3.2",
                "created_at": "2026-02-16T12:00:00Z",
                "updated_at": "2026-02-16T12:00:00Z",
                "messages": [
                    {
                        "id": 1,
                        "role": "user",
                        "content": "What is Python?",
                        "created_at": "2026-02-16T12:00:00Z",
                    },
                    {
                        "id": 2,
                        "role": "assistant",
                        "content": "Python is a programming language...",
                        "created_at": "2026-02-16T12:00:01Z",
                    },
                ],
            }
        },
    }


class ConversationListResponse(BaseModel):
    """Schema for listing conversations with pagination info."""

    conversations: list[ConversationResponse] = Field(
        ..., description="List of conversations"
    )
    total: int = Field(..., example=10, description="Total number of conversations")
