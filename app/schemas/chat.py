"""Chat-related schemas."""

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Schema for sending a single chat message to the LLM."""

    message: str = Field(
        ...,
        min_length=1,
        description="The user's message",
        example="What is the capital of France?",
    )
    model: str | None = Field(
        default=None,
        description="Ollama model name (uses server default if omitted)",
        example="llama3.2",
    )
    use_rag: bool = Field(
        default=False,
        description="Augment with RAG context from document store",
    )


class ChatMessageResponse(BaseModel):
    """Schema for a complete (non-streaming) chat response."""

    response: str = Field(
        ...,
        description="The LLM's complete response text",
        example="The capital of France is Paris.",
    )
    model: str = Field(
        ...,
        description="The model that generated the response",
        example="llama3.2",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "response": "The capital of France is Paris.",
                "model": "llama3.2",
            }
        }
    }


class ChatStreamEvent(BaseModel):
    """Schema for a single SSE stream event (for documentation)."""

    token: str | None = Field(
        default=None,
        description="A token fragment from the LLM response",
    )
    done: bool | None = Field(
        default=None,
        description="True when the stream is complete",
    )
    error: str | None = Field(
        default=None,
        description="Error message if something went wrong",
    )
