"""Tests for JWT authentication endpoints.

Uses sha256_crypt (not bcrypt) for test password hashing to avoid passlib/bcrypt
version-compatibility issues on Windows. The monkeypatch replaces the production
CryptContext so hash_password and verify_password both use the same scheme.
"""

import pytest
from passlib.context import CryptContext

from app.auth.jwt import create_access_token
from app.config import settings
from app.models.user import User

# Lighter scheme — avoids bcrypt >= 4.0 compatibility issues in tests
_TEST_CTX = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


# ── Module-level fixtures ─────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def use_test_crypto(monkeypatch):
    """Replace bcrypt CryptContext with sha256_crypt for all auth tests."""
    monkeypatch.setattr("app.auth.jwt.pwd_context", _TEST_CTX)


@pytest.fixture(autouse=True)
def clean_auth_state():
    """Reset rate-limit and lockout state before each auth test.

    Two independent mechanisms can return 429 on POST /auth/login:
      1. slowapi @limiter.limit("5/minute") — exhausted across TestLogin tests.
      2. lockout service — Redis counters persist across test sessions.
    Both are cleared here so tests are fully isolated.
    """
    from app.limiter import limiter
    from app import cache

    limiter.enabled = False

    r = cache._client()
    if r is not None:
        try:
            keys = r.keys("login_fail:*")
            if keys:
                r.delete(*keys)
        except Exception:
            pass

    yield
    limiter.enabled = True


@pytest.fixture
def jwt_secret(monkeypatch):
    """Temporarily inject a known JWT secret so tokens can be created/verified."""
    original = settings.jwt_secret_key
    object.__setattr__(settings, "jwt_secret_key", "test-jwt-secret-for-pytest")
    yield "test-jwt-secret-for-pytest"
    object.__setattr__(settings, "jwt_secret_key", original)


@pytest.fixture
def analyst_user(db):
    user = User(
        username="analyst",
        hashed_password=_TEST_CTX.hash("analystpass"),
        role="analyst",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db):
    user = User(
        username="admin",
        hashed_password=_TEST_CTX.hash("adminpass"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, username: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.json()
    return resp.json()["access_token"]


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_returns_501_when_jwt_not_configured(self, client):
        from app.config import settings as _settings
        original = _settings.jwt_secret_key
        object.__setattr__(_settings, "jwt_secret_key", "")
        try:
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": "x", "password": "y"},
            )
            assert resp.status_code == 501
        finally:
            object.__setattr__(_settings, "jwt_secret_key", original)

    def test_login_success(self, client, analyst_user, jwt_secret):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "analyst", "password": "analystpass"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "analyst"
        assert data["role"] == "analyst"

    def test_login_wrong_password(self, client, analyst_user, jwt_secret):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "analyst", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self, client, jwt_secret):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "pass"},
        )
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, db, jwt_secret):
        db.add(User(
            username="inactive",
            hashed_password=_TEST_CTX.hash("pass"),
            role="analyst",
            is_active=False,
        ))
        db.commit()
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "inactive", "password": "pass"},
        )
        assert resp.status_code == 401


# ── /me ───────────────────────────────────────────────────────────────────────

class TestGetMe:
    def test_me_requires_auth(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)

    def test_me_with_invalid_token(self, client, jwt_secret):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        assert resp.status_code in (401, 403)

    def test_me_returns_current_user(self, client, analyst_user, jwt_secret):
        token = _login(client, "analyst", "analystpass")
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "analyst"
        assert data["role"] == "analyst"

    def test_me_returns_admin_role(self, client, admin_user, jwt_secret):
        token = _login(client, "admin", "adminpass")
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"


# ── Register ──────────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_requires_auth(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "new", "password": "pass", "role": "analyst"},
        )
        assert resp.status_code in (401, 403)

    def test_register_requires_admin_role(self, client, analyst_user, jwt_secret):
        token = _login(client, "analyst", "analystpass")
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "new", "password": "pass", "role": "analyst"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_register_as_admin_creates_user(self, client, admin_user, jwt_secret):
        token = _login(client, "admin", "adminpass")
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "newanalyst", "password": "Secure123", "role": "analyst"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "newanalyst"
        assert data["role"] == "analyst"

    def test_register_duplicate_username_returns_409(self, client, admin_user, analyst_user, jwt_secret):
        token = _login(client, "admin", "adminpass")
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "analyst", "password": "Duplicate1", "role": "analyst"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409
