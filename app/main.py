"""Main FastAPI application entry point."""

from fastapi import FastAPI

from app.config import get_settings
from app.routes import auth, chat, conversations, rag, system, users
from app.schemas.system import RootResponse
from app.handlers import register_exception_handlers

app = FastAPI(
    title=get_settings().app_name,
    version=get_settings().app_version
)

# Register global exception handlers
register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(system.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(rag.router)


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    """Root endpoint returning a welcome message."""
    return RootResponse(message="Welcome to the AI Chatbot API")
