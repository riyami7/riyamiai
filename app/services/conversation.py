"""Service layer for conversation business logic."""

import json
from datetime import datetime, timezone
from typing import AsyncGenerator

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.conversation import ConversationCreate, ConversationUpdate
from app.schemas.message import MessageCreate
from app.repositories.conversation import ConversationRepository
from app.services.ollama_service import chat_completion, chat_completion_stream
from app.services.rag import RagService
from app.exceptions import NotFoundError, ServiceUnavailableError, ForbiddenError


class ConversationService:
    """Service class for conversation-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = ConversationRepository(db)
        self.settings = get_settings()
        self._rag_service = RagService(db)

    # ──────────────────────────────────────────────
    # Conversation CRUD
    # ──────────────────────────────────────────────

    def create(self, data: ConversationCreate, user: User) -> Conversation:
        """Create a new conversation.

        Args:
            data: Conversation creation data.
            user: The authenticated user.

        Returns:
            The created conversation.
        """
        conversation = Conversation(
            user_id=user.id,
            title="New conversation",  # Will be auto-updated on first message
            model=data.model or self.settings.ollama_default_model,
        )
        return self.repository.create(conversation)

    def get_by_id(self, conversation_id: int, user: User) -> Conversation:
        """Get a conversation by ID, ensuring the user owns it.

        Args:
            conversation_id: The conversation's ID.
            user: The authenticated user.

        Returns:
            The conversation.

        Raises:
            NotFoundError: If conversation not found or not owned by user.
        """
        conversation = self.repository.get_by_id_and_user(conversation_id, user.id)
        if conversation is None:
            raise NotFoundError(
                detail="Conversation not found",
                error_code="CONVERSATION_NOT_FOUND",
                context={"conversation_id": conversation_id},
            )
        return conversation

    def get_all(
        self, user: User, skip: int = 0, limit: int = 100
    ) -> tuple[list[Conversation], int]:
        """Get all conversations for a user with pagination.

        Args:
            user: The authenticated user.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (conversations list, total count).
        """
        conversations = self.repository.get_all_by_user(user.id, skip=skip, limit=limit)
        total = self.repository.count_by_user(user.id)
        return conversations, total

    def update(
        self, conversation_id: int, data: ConversationUpdate, user: User
    ) -> Conversation:
        """Update an existing conversation.

        Args:
            conversation_id: The conversation's ID.
            data: Conversation update data.
            user: The authenticated user.

        Returns:
            The updated conversation.

        Raises:
            NotFoundError: If conversation not found or not owned by user.
        """
        conversation = self.get_by_id(conversation_id, user)

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return conversation

        for field, value in update_data.items():
            setattr(conversation, field, value)

        conversation.updated_at = datetime.now(timezone.utc)
        return self.repository.update(conversation)

    def delete(self, conversation_id: int, user: User) -> None:
        """Delete a conversation by ID.

        Args:
            conversation_id: The conversation's ID.
            user: The authenticated user.

        Raises:
            NotFoundError: If conversation not found or not owned by user.
        """
        conversation = self.get_by_id(conversation_id, user)
        self.repository.delete(conversation)

    # ──────────────────────────────────────────────
    # Message Operations
    # ──────────────────────────────────────────────

    async def _build_llm_messages(
        self,
        conversation: Conversation,
        user: User,
        new_message: str,
        use_rag: bool = False,
    ) -> list[dict]:
        """Build the message list for the Ollama API.

        Loads the last N messages from the conversation and prepends
        the system prompt from the user's profile.

        Args:
            conversation: The conversation.
            user: The authenticated user (provides system_prompt).
            new_message: The new user message to append.
            use_rag: Whether to augment with RAG context.

        Returns:
            A list of message dicts with 'role' and 'content'.
        """
        # Get the last N messages for context
        context_limit = self.settings.ollama_context_message_limit
        db_messages = self.repository.get_messages(
            conversation.id, limit=context_limit
        )

        # Build system prompt, optionally with RAG context
        system_prompt = user.system_prompt
        if use_rag:
            rag_context = await self._rag_service.get_context(new_message)
            if rag_context:
                system_prompt = f"{rag_context}\n\n{system_prompt}"

        # Build the messages list
        messages = [{"role": "system", "content": system_prompt}]

        for msg in db_messages:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the new user message
        messages.append({"role": "user", "content": new_message})

        return messages

    def _auto_generate_title(self, conversation: Conversation, first_message: str) -> None:
        """Auto-generate the conversation title from the first message.

        Args:
            conversation: The conversation to update.
            first_message: The first user message.
        """
        # Truncate to ~50 chars at a word boundary
        title = first_message[:50]
        if len(first_message) > 50:
            # Try to break at last space
            last_space = title.rfind(" ")
            if last_space > 20:
                title = title[:last_space]
            title += "..."

        conversation.title = title
        self.repository.update(conversation)

    async def send_message(
        self, conversation_id: int, data: MessageCreate, user: User
    ) -> tuple[Message, Message]:
        """Send a message in a conversation and get the LLM response.

        Args:
            conversation_id: The conversation's ID.
            data: Message creation data.
            user: The authenticated user.

        Returns:
            Tuple of (user_message, assistant_message).

        Raises:
            NotFoundError: If conversation not found or not owned by user.
            ServiceUnavailableError: If Ollama is unreachable.
        """
        conversation = self.get_by_id(conversation_id, user)

        # Check if this is the first message for auto-title
        is_first_message = self.repository.count_messages(conversation.id) == 0

        # Build messages for LLM (with optional RAG augmentation)
        llm_messages = await self._build_llm_messages(
            conversation, user, data.content, use_rag=data.use_rag
        )

        # Save the user message
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=data.content,
        )
        self.repository.create_message(user_message)

        # Call the LLM
        try:
            result = await chat_completion(llm_messages, model=conversation.model)
        except httpx.ConnectError:
            raise ServiceUnavailableError(
                detail="Cannot connect to Ollama. Is it running?",
                error_code="OLLAMA_UNAVAILABLE",
                context={"ollama_model": conversation.model},
            )

        # Save the assistant message
        assistant_content = result["message"]["content"]
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
        )
        self.repository.create_message(assistant_message)

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)
        self.repository.update(conversation)

        # Auto-generate title if first message
        if is_first_message:
            self._auto_generate_title(conversation, data.content)

        return user_message, assistant_message

    async def stream_message(
        self, conversation_id: int, data: MessageCreate, user: User
    ) -> AsyncGenerator[str, None]:
        """Send a message and stream the LLM response as SSE events.

        The response is accumulated and saved to DB after the stream completes.

        Args:
            conversation_id: The conversation's ID.
            data: Message creation data.
            user: The authenticated user.

        Yields:
            SSE-formatted event strings.

        Raises:
            NotFoundError: If conversation not found or not owned by user.
        """
        conversation = self.get_by_id(conversation_id, user)

        # Check if this is the first message for auto-title
        is_first_message = self.repository.count_messages(conversation.id) == 0

        # Build messages for LLM (with optional RAG augmentation)
        llm_messages = await self._build_llm_messages(
            conversation, user, data.content, use_rag=data.use_rag
        )

        # Save the user message
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=data.content,
        )
        self.repository.create_message(user_message)

        # Accumulate the response
        accumulated_response = []

        try:
            async for token in chat_completion_stream(
                llm_messages, model=conversation.model
            ):
                accumulated_response.append(token)
                event_data = json.dumps({"token": token})
                yield f"data: {event_data}\n\n"

            # Stream complete - save the assistant message
            full_response = "".join(accumulated_response)
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=full_response,
            )
            self.repository.create_message(assistant_message)

            # Update conversation timestamp
            conversation.updated_at = datetime.now(timezone.utc)
            self.repository.update(conversation)

            # Auto-generate title if first message
            if is_first_message:
                self._auto_generate_title(conversation, data.content)

            yield f"data: {json.dumps({'done': True})}\n\n"

        except httpx.ConnectError:
            error = json.dumps({"error": "Cannot connect to Ollama"})
            yield f"data: {error}\n\n"

    def get_messages(self, conversation_id: int, user: User) -> list[Message]:
        """Get all messages for a conversation.

        Args:
            conversation_id: The conversation's ID.
            user: The authenticated user.

        Returns:
            List of messages.

        Raises:
            NotFoundError: If conversation not found or not owned by user.
        """
        conversation = self.get_by_id(conversation_id, user)
        return self.repository.get_messages(conversation.id)
