"""Webhook notification service.

Sends HTTP POST payloads to WEBHOOK_URL for critical alert events and
ingestion failure streaks. Fire-and-forget: failures are logged, not raised.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_webhook(payload: dict) -> None:
    """POST payload to the configured WEBHOOK_URL.

    Silently returns if WEBHOOK_URL is not configured.
    Compatible with Slack, Discord, n8n, and generic webhooks.
    """
    if not settings.webhook_url:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings.webhook_url, json=payload)
            resp.raise_for_status()
            logger.debug(
                "[webhook] Sent event=%s", payload.get("event", "unknown")
            )
    except Exception as exc:
        logger.warning("[webhook] Notification failed: %s", exc)
