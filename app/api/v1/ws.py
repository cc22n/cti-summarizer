"""WebSocket endpoint for real-time alert notifications.

Subscribes to the Redis Pub/Sub channel 'channel:alerts:new' and
forwards each message to connected WebSocket clients.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

_CHANNEL = "channel:alerts:new"


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    """Stream new critical/high alert events via WebSocket.

    Each message is a JSON string published to the Redis channel
    by the ingestion orchestrator when critical or high alerts arrive.
    """
    await websocket.accept()
    logger.info("[ws] Client connected: %s", websocket.client)

    try:
        import redis.asyncio as aioredis
        from app.config import settings

        client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        pubsub = client.pubsub()
        await pubsub.subscribe(_CHANNEL)

        async def _read_messages():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message.get("data", "")
                    try:
                        await websocket.send_text(data)
                    except WebSocketDisconnect:
                        return

        try:
            await asyncio.wait_for(_read_messages(), timeout=None)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        finally:
            await pubsub.unsubscribe(_CHANNEL)
            await client.aclose()

    except ImportError:
        logger.warning("[ws] redis.asyncio not available - WebSocket closed immediately")
        await websocket.close(code=1011)
    except Exception as exc:
        logger.error("[ws] Unexpected error: %s", exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass

    logger.info("[ws] Client disconnected: %s", websocket.client)
