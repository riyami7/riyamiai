"""Notification utilities for sending alerts via external services."""

import httpx

from app.config import get_settings


async def send_telegram_notification(message: str) -> bool:
    """Send a notification message via Telegram bot.

    Args:
        message: The message to send (supports HTML formatting).

    Returns:
        True if sent successfully, False otherwise.
    """
    settings = get_settings()

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False  # Notifications not configured

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
                timeout=10.0,
            )
            return response.status_code == 200
    except Exception:
        return False  # Fail silently - notifications are non-critical
