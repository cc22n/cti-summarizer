"""Shared slowapi rate limiter instance.

Import this module to access the limiter:
    from app.limiter import limiter

Apply per-endpoint with:
    @router.post("/endpoint")
    @limiter.limit("30/minute")
    def my_endpoint(request: Request, ...):
        ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
