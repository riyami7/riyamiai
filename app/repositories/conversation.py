"""Repository for conversation data access operations."""

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


class ConversationRepository:
    """Repository class for conversation and message data access."""

    def __init__(self, db: Session):
        self.db = db

    # ──────────────────────────────────────────────
    # Conversation Methods
    # ──────────────────────────────────────────────

    def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation.

        Args:
            conversation: Conversation model instance to create.

        Returns:
            The created conversation with ID populated.
        """
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_by_id(self, conversation_id: int) -> Conversation | None:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation's ID.

        Returns:
            The conversation if found, None otherwise.
        """
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

    def get_by_id_and_user(
        self, conversation_id: int, user_id: int
    ) -> Conversation | None:
        """Get a conversation by ID, scoped to a specific user.

        Args:
            conversation_id: The conversation's ID.
            user_id: The user's ID.

        Returns:
            The conversation if found and owned by user, None otherwise.
        """
        return (
            self.db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )

    def get_all_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Conversation]:
        """Get all conversations for a user with pagination.

        Args:
            user_id: The user's ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of conversations owned by the user.
        """
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_user(self, user_id: int) -> int:
        """Get total count of conversations for a user.

        Args:
            user_id: The user's ID.

        Returns:
            Total number of conversations for the user.
        """
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .count()
        )

    def update(self, conversation: Conversation) -> Conversation:
        """Update a conversation.

        Args:
            conversation: Conversation model instance with updated fields.

        Returns:
            The updated conversation.
        """
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def delete(self, conversation: Conversation) -> None:
        """Delete a conversation and all its messages.

        Args:
            conversation: Conversation model instance to delete.
        """
        self.db.delete(conversation)
        self.db.commit()

    # ──────────────────────────────────────────────
    # Message Methods
    # ──────────────────────────────────────────────

    def create_message(self, message: Message) -> Message:
        """Create a new message.

        Args:
            message: Message model instance to create.

        Returns:
            The created message with ID populated.
        """
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_messages(
        self, conversation_id: int, limit: int | None = None
    ) -> list[Message]:
        """Get messages for a conversation.

        Args:
            conversation_id: The conversation's ID.
            limit: Maximum number of messages to return (most recent).
                   If None, returns all messages.

        Returns:
            List of messages, ordered by created_at ascending.
        """
        query = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )

        if limit is not None:
            # Get the last N messages by ordering desc, limiting, then reversing
            messages = (
                self.db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
                .all()
            )
            return list(reversed(messages))

        return query.all()

    def count_messages(self, conversation_id: int) -> int:
        """Get total count of messages in a conversation.

        Args:
            conversation_id: The conversation's ID.

        Returns:
            Total number of messages.
        """
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .count()
        )
