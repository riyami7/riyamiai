"""Chat routes for LLM interaction."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.schemas.error import ErrorResponse
from app.services.chat import ChatService
from app.models.user import User
from app.dependencies.auth import get_current_user

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"],
)


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    """Dependency to get ChatService instance."""
    return ChatService(db)


@router.post(
    "/single",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Ollama service unavailable"},
    },
)
async def single_message(
    request: ChatMessageRequest,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    """Send a single message to the LLM and get a complete response (auth required).

    No conversation history — each request is independent.
    System prompt is taken from the authenticated user's profile.
    """
    return await service.send_message(request, current_user)


@router.post(
    "/single/stream",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Ollama service unavailable"},
    },
)
async def single_message_stream(
    request: ChatMessageRequest,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Send a single message and stream the response via SSE (auth required).

    Each event contains a token fragment. The final event has `done: true`.
    System prompt is taken from the authenticated user's profile.
    """
    return StreamingResponse(
        service.stream_message(request, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
