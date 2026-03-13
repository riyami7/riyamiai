from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    app_name: str = "AI Chatbot API"
    app_version: str = "0.1.0"
    env: str = "development"
    debug: bool = False
    database_url: str = "postgresql://localhost:5432/ai_chatbot"

    # JWT settings
    jwt_secret_key: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2"
    ollama_timeout_seconds: int = 120
    ollama_context_message_limit: int = 10

    # RAG settings
    rag_embedding_model: str = "nomic-embed-text"
    rag_embedding_dimension: int = 768
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_search_top_k: int = 5
    rag_data_dir: str = "app/data"

    # Telegram notifications
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - loaded once, reused everywhere."""
    return Settings()