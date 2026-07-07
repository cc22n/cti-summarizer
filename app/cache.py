"""Redis cache helpers for read endpoints.

Non-fatal: all operations catch exceptions and fall back silently so
the application keeps working even when Redis is unavailable.
"""

import json
import logging

logger = logging.getLogger(__name__)

_redis_client = None


def _client():
    """Return a Redis client, initialising it lazily on first call."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as _redis
        from app.config import settings

        _redis_client = _redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        return _redis_client
    except Exception as exc:
        logger.warning("[cache] Redis init failed: %s", exc)
        return None


def get_cached(key: str):
    """Return cached value (parsed JSON) or None on miss / error."""
    r = _client()
    if r is None:
        return None
    try:
        data = r.get(key)
        return json.loads(data) if data else None
    except Exception as exc:
        logger.warning("[cache] get(%s) failed: %s", key, exc)
        return None


def set_cached(key: str, data, ttl: int = 60) -> None:
    """Serialize data to JSON and store with expiry TTL seconds."""
    r = _client()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(data, default=str))
    except Exception as exc:
        logger.warning("[cache] set(%s) failed: %s", key, exc)


def invalidate(key: str) -> None:
    """Delete a cache key (best-effort)."""
    r = _client()
    if r is None:
        return
    try:
        r.delete(key)
    except Exception as exc:
        logger.warning("[cache] invalidate(%s) failed: %s", key, exc)
