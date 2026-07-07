"""Authentication API endpoints (JWT-based)."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user, require_admin
from app.auth.jwt import create_access_token, hash_password, verify_password
from app.auth.lockout import clear_failures, is_locked_out, record_failure
from app.database import get_db
from app.limiter import limiter
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Obtain a JWT access token")
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with username + password and receive a Bearer token.

    Rate-limited to 5 attempts per minute per IP. After 5 consecutive
    failures the account is locked for 15 minutes (tracked in Redis).
    """
    from app.config import settings

    if not settings.jwt_secret_key:
        raise HTTPException(
            status_code=501,
            detail="JWT authentication is not configured (set JWT_SECRET_KEY in .env)",
        )

    client_ip = request.client.host if request.client else "unknown"

    if is_locked_out(body.username, client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again in 15 minutes.",
        )

    user = (
        db.query(User)
        .filter(User.username == body.username, User.is_active == True)
        .first()
    )

    if not user or not verify_password(body.password, user.hashed_password):
        record_failure(body.username, client_ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    clear_failures(body.username, client_ip)
    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse, summary="Get current user info")
def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/register",
    response_model=UserResponse,
    summary="Create a new user (admin only)",
)
def register(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Create a new user account. Requires admin role."""
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse], summary="List users (admin only)")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all users. Requires admin role."""
    users = db.query(User).order_by(User.username).all()
    return [UserResponse.model_validate(u) for u in users]
