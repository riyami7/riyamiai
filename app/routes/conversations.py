"""Conversation routes for persistent chat history."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
)
from app.schemas.message import MessageCreate, AssistantMessageResponse, MessageResponse
from app.schemas.error import ErrorResponse
from app.services.conversation import ConversationService
from app.models.user import User
from app.dependencies.auth import get_current_user

router = APIRouter(
    prefix="/api/conversations",
    tags=["Conversations"],
)


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """Dependency to get ConversationService instance."""
    return ConversationService(db)


# ──────────────────────────────────────────────
# Conversation CRUD Endpoints
# ──────────────────────────────────────────────


@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def create_conversation(
    data: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    """Create a new conversation (auth required).

    Optionally specify a model, otherwise the server default is used.
    """
    conversation = service.create(data, current_user)
    return ConversationResponse.model_validate(conversation)


@router.get(
    "/",
    response_model=ConversationListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def list_conversations(
    skip: int = 0,
    limit: int = 100,
    service: ConversationService = Depends(get_conversation_service),
    current_user: User = Depends(get_current_user),
) -> ConversationListResponse:
    """List all conversations for the authenticated user (auth required)."""
    conversations, total = service.get_all(current_user, skip=skip, limit=limit)
    return ConversationListResponse(
        conversations=[
            ConversationResponse.model_validate(c) for c in conversations
        ],
        total=total,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def get_conversation(
    conversation_id: int,
    service: ConversationService = Depends(get_conversation_service),
    current_user: User = Depends(get_current_user),
) -> ConversationDetailResponse:
    """Get a specific conversation with all its messages (auth required)."""
    conversation = service.get_by_id(conversation_id, current_user)
    messages = service.get_messages(conversation_id, current_user)

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        model=conversation.model,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.put(
    "/{conversation_id}",
    response_model=ConversationResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    service: ConversationService = Depends(get_conversation_service),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    """Update a conversation's title (auth required)."""
    conversation = service.update(conversation_id, data, current_user)
    return ConversationResponse.model_validate(conversation)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def delete_conversation(
    conversation_id: int,
    service: ConversationService = Depends(get_conversation_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a conversation and all its messages (auth required)."""
    service.delete(conversation_id, current_user)


# ──────────────────────────────────────────────
# Message Endpoints
# ──────────────────────────────────────────────


@router.post(
    "/{conversation_id}/messages",
    response_model=AssistantMessageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
        503: {"model": ErrorResponse, "description": "Ollama service unavailable"},
    },
)
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    service: ConversationService = Depends(get_conversation_service),
    current_user: User = Depends(get_current_user),
) -> AssistantMessageResponse:
    """Send a message in a conversation and get the LLM response (auth required).

    The user's message and the assistant's response are both saved to the conversation.
    System prompt is taken from the authenticated user's profile.
    """
    user_message, assistant_message = await service.send_message(
        conversation_id, data, current_user
    )
    return AssistantMessageResponse(
        user_message=MessageResponse.model_validate(user_message),
        assistant_message=MessageResponse.model_validate(assistant_message),
    )


@router.post(
    "/{conversation_id}/messages/stream",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
        503: {"model": ErrorResponse, "description": "Ollama service unavailable"},
    },
)
async def send_message_stream(
    conversation_id: int,
    data: MessageCreate,
    service: ConversationService = Depends(get_conversation_service),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Send a message and stream the LLM response via SSE (auth required).

    Each event contains a token fragment. The final event has `done: true`.
    Both messages are saved to the conversation after the stream completes.
    System prompt is taken from the authenticated user's profile.
    """
    return StreamingResponse(
        service.stream_message(conversation_id, data, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
