"""Low-level Ollama HTTP client.

Handles raw HTTP communication with the Ollama API.
Business logic belongs in ChatService, not here.
"""

import json
from typing import AsyncGenerator

import httpx

from app.config import get_settings


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
) -> dict:
    """Send messages to Ollama and get a complete response.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        model: Ollama model name. Uses config default if omitted.

    Returns:
        The full Ollama response as a dict.

    Raises:
        httpx.ConnectError: If Ollama is unreachable.
        httpx.HTTPStatusError: If Ollama returns an error status.
    """
    settings = get_settings()
    model = model or settings.ollama_default_model

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
            },
            timeout=float(settings.ollama_timeout_seconds),
        )
        response.raise_for_status()
        return response.json()


async def chat_completion_stream(
    messages: list[dict],
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Send messages to Ollama and stream the response token by token.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        model: Ollama model name. Uses config default if omitted.

    Yields:
        Each content fragment as it arrives from Ollama.

    Raises:
        httpx.ConnectError: If Ollama is unreachable.
        httpx.HTTPStatusError: If Ollama returns an error status.
    """
    settings = get_settings()
    model = model or settings.ollama_default_model

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
            },
            timeout=float(settings.ollama_timeout_seconds),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
                if chunk.get("done", False):
                    break
