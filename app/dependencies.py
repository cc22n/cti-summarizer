"""FastAPI shared dependencies.

Write-access guard: accepts JWT Bearer token, X-API-Key header, or neither
(dev mode bypass when no auth is configured).
"""

import hmac

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyHeader
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    api_key: str | None = Security(_api_key_header),
    db: Session = Depends(get_db),
) -> None:
    """Unified write-access guard: JWT Bearer > X-API-Key > dev bypass.

    - If jwt_secret_key is set: validate Bearer token.
    - Else if api_key is set: validate X-API-Key header.
    - Else: bypass (dev / test mode with no auth configured).
    """
    # Dev/test mode: no auth configured at all
    if not settings.jwt_secret_key and not settings.api_key:
        return

    # JWT Bearer path
    if settings.jwt_secret_key and credentials:
        try:
            from jose import jwt as jose_jwt

            payload = jose_jwt.decode(
                credentials.credentials,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            username = payload.get("sub")
            if not username:
                raise HTTPException(status_code=401, detail="Invalid token")
            from app.models.user import User

            user = (
                db.query(User)
                .filter(User.username == username, User.is_active == True)
                .first()
            )
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            return  # valid JWT
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # X-API-Key legacy path (timing-safe comparison to prevent timing attacks)
    if settings.api_key and hmac.compare_digest(api_key or "", settings.api_key):
        return

    # Nothing matched
    detail = "Authentication required (Bearer token or X-API-Key)"
    raise HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
