"""
AURA Notification Service — Telegram
--------------------------------------
Sends messages to a Telegram chat via the Bot API.

Setup:
  1. Create a bot via @BotFather on Telegram → get TELEGRAM_BOT_TOKEN
  2. Send any message to your bot
  3. Visit https://api.telegram.org/bot<TOKEN>/getUpdates to find your chat ID
  4. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env

Usage:
    from app.notifications.telegram import send_notification
    send_notification("Hello from AURA!")
"""
from __future__ import annotations

import logging
from typing import Optional
import httpx

from app.database.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_notification(message: str, chat_id: Optional[str] = None) -> bool:
    """
    Send a Telegram message to the configured chat.

    Args:
        message: The text to send (supports Markdown).
        chat_id: Override the default chat ID from settings.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    target_chat = chat_id or settings.TELEGRAM_CHAT_ID

    if not token or token == "your_telegram_bot_token_here":
        logger.warning("[Telegram] Bot token not configured. Skipping notification.")
        return False

    if not target_chat:
        logger.warning("[Telegram] Chat ID not configured. Skipping notification.")
        return False

    url = TELEGRAM_API_URL.format(token=token)
    payload = {
        "chat_id": target_chat,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        resp = httpx.post(url, json=payload, timeout=10.0)
        resp.raise_for_status()
        logger.info(f"[Telegram] Notification sent: {message[:80]}...")
        return True
    except httpx.HTTPStatusError as e:
        logger.error(f"[Telegram] HTTP error: {e.response.status_code} — {e.response.text}")
    except Exception as e:
        logger.error(f"[Telegram] Failed to send notification: {e}")
    return False


def send_task_reminder(title: str, due_str: str) -> bool:
    """Convenience wrapper for task reminder notifications."""
    message = f"⏰ *AURA Reminder*\n\nTask: *{title}*\nDue: {due_str}"
    return send_notification(message)


def send_daily_summary(summary: str) -> bool:
    """Send the daily morning summary to Telegram."""
    message = f"🌅 *Good Morning, AURA Daily Summary*\n\n{summary}"
    return send_notification(message)
