"""Login brute-force protection via Redis-backed attempt counters.

Tracks failed attempts per IP address and per username separately so
that both a targeted attack on a specific account and a credential
spray from one IP are caught.

Degrades gracefully: when Redis is unavailable every check returns
False and no writes are attempted, so the application keeps working.
"""

import logging

from app import cache

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900  # 15 minutes


def _ip_key(ip: str) -> str:
    return f"login_fail:ip:{ip}"


def _user_key(username: str) -> str:
    return f"login_fail:user:{username}"


def is_locked_out(username: str, ip: str) -> bool:
    """Return True if the username or IP has exceeded the failure threshold."""
    r = cache._client()
    if r is None:
        return False
    try:
        ip_count = int(r.get(_ip_key(ip)) or 0)
        user_count = int(r.get(_user_key(username)) or 0)
        return ip_count >= _MAX_ATTEMPTS or user_count >= _MAX_ATTEMPTS
    except Exception as exc:
        logger.warning("[lockout] Redis read failed: %s", exc)
        return False


def record_failure(username: str, ip: str) -> None:
    """Increment failure counters and set/refresh the lockout TTL."""
    r = cache._client()
    if r is None:
        return
    try:
        pipe = r.pipeline()
        for key in (_ip_key(ip), _user_key(username)):
            pipe.incr(key)
            pipe.expire(key, _LOCKOUT_SECONDS)
        pipe.execute()
    except Exception as exc:
        logger.warning("[lockout] record_failure failed: %s", exc)


def clear_failures(username: str, ip: str) -> None:
    """Delete failure counters after a successful login."""
    r = cache._client()
    if r is None:
        return
    try:
        r.delete(_ip_key(ip), _user_key(username))
    except Exception as exc:
        logger.warning("[lockout] clear_failures failed: %s", exc)
