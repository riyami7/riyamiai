"""Service layer for chat business logic."""

import json
from typing import AsyncGenerator

import httpx
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.ollama_service import chat_completion, chat_completion_stream
from app.services.rag import RagService
from app.exceptions import ServiceUnavailableError


class ChatService:
    """Service class for chat-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self._rag_service = RagService(db)

    async def _build_messages(
        self, request: ChatMessageRequest, system_prompt: str
    ) -> list[dict]:
        """Build the message list for the Ollama API.

        Args:
            request: The incoming chat request.
            system_prompt: The system prompt from the user's profile.

        Returns:
            A list of message dicts with 'role' and 'content'.
        """
        # If RAG is enabled, prepend context to system prompt
        effective_system_prompt = system_prompt
        if request.use_rag:
            rag_context = await self._rag_service.get_context(request.message)
            if rag_context:
                effective_system_prompt = f"{rag_context}\n\n{system_prompt}"

        return [
            {"role": "system", "content": effective_system_prompt},
            {"role": "user", "content": request.message},
        ]

    async def send_message(
        self, request: ChatMessageRequest, user: User
    ) -> ChatMessageResponse:
        """Send a single message to the LLM and return the complete response.

        Args:
            request: The chat message request.
            user: The authenticated user (provides system_prompt).

        Returns:
            The LLM's complete response.

        Raises:
            ServiceUnavailableError: If Ollama is unreachable.
        """
        messages = await self._build_messages(request, user.system_prompt)

        try:
            result = await chat_completion(messages, model=request.model)
        except httpx.ConnectError:
            raise ServiceUnavailableError(
                detail="Cannot connect to Ollama. Is it running?",
                error_code="OLLAMA_UNAVAILABLE",
                context={"ollama_model": request.model},
            )

        return ChatMessageResponse(
            response=result["message"]["content"],
            model=result["model"],
        )

    async def stream_message(
        self, request: ChatMessageRequest, user: User
    ) -> AsyncGenerator[str, None]:
        """Send a single message and stream the response as SSE events.

        Each yielded string is a complete SSE event (data: {...}\\n\\n).

        Args:
            request: The chat message request.
            user: The authenticated user (provides system_prompt).

        Yields:
            SSE-formatted event strings.

        Raises:
            ServiceUnavailableError: If Ollama is unreachable.
        """
        messages = await self._build_messages(request, user.system_prompt)

        try:
            async for token in chat_completion_stream(
                messages, model=request.model
            ):
                event_data = json.dumps({"token": token})
                yield f"data: {event_data}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except httpx.ConnectError:
            error = json.dumps({"error": "Cannot connect to Ollama"})
            yield f"data: {error}\n\n"
