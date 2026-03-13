"""Schema exports for the AI Chatbot API."""

from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatStreamEvent
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
)
from app.schemas.health import HealthResponse, HealthStatus
from app.schemas.message import MessageCreate, MessageResponse, AssistantMessageResponse
from app.schemas.rag import (
    RagIngestJobResponse,
    RagIngestJobStatus,
    RagIngestResponse,
    RagIngestResult,
    RagSearchRequest,
    RagSearchResult,
    RagSearchResponse,
)
from app.schemas.system import SystemInfoResponse, ConfigResponse, RootResponse
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
)

__all__ = [
    "LoginRequest",
    "TokenResponse",
    "ChatMessageRequest",
    "ChatMessageResponse",
    "ChatStreamEvent",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationDetailResponse",
    "ConversationListResponse",
    "HealthResponse",
    "HealthStatus",
    "MessageCreate",
    "MessageResponse",
    "AssistantMessageResponse",
    "RagIngestJobResponse",
    "RagIngestJobStatus",
    "RagIngestResponse",
    "RagIngestResult",
    "RagSearchRequest",
    "RagSearchResult",
    "RagSearchResponse",
    "SystemInfoResponse",
    "ConfigResponse",
    "RootResponse",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
]
