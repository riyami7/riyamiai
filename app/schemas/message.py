"""Message-related schemas."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"


class MessageCreate(BaseModel):
    """Schema for sending a new message in a conversation."""

    content: str = Field(
        ...,
        min_length=1,
        description="The message content",
        example="What is the capital of France?",
    )
    use_rag: bool = Field(
        default=False,
        description="Augment with RAG context from document store",
    )


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: int = Field(..., example=1, description="Unique message identifier")
    role: MessageRole = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Timestamp when the message was created")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "role": "user",
                "content": "What is the capital of France?",
                "created_at": "2026-02-16T12:00:00Z",
            }
        },
    }


class AssistantMessageResponse(BaseModel):
    """Schema for assistant response after sending a message."""

    user_message: MessageResponse = Field(
        ..., description="The user's message that was sent"
    )
    assistant_message: MessageResponse = Field(
        ..., description="The assistant's response"
    )
