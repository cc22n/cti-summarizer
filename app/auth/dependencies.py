"""FastAPI auth dependencies for JWT + role-based access."""

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.config import settings
from app.database import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def _get_user_from_token(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
) -> User | None:
    """Validate Bearer JWT and return the User, or None if no token."""
    if not credentials:
        return None
    if not settings.jwt_secret_key:
        return None
    try:
        payload = decode_token(credentials.credentials)
        username: str | None = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = (
            db.query(User)
            .filter(User.username == username, User.is_active == True)
            .first()
        )
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Require a valid JWT Bearer token. Raises 401 if not present or invalid."""
    user = _get_user_from_token(credentials, db)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to have the admin role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_write_access(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Accept JWT Bearer token or bypass in dev mode.

    Priority:
      1. JWT Bearer (if jwt_secret_key is configured and credentials present)
      2. Dev mode bypass (if jwt_secret_key is not set)
    """
    if not settings.jwt_secret_key:
        return None  # dev mode or JWT not configured

    if credentials:
        # _get_user_from_token raises HTTPException on invalid token
        user = _get_user_from_token(credentials, db)
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
