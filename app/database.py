"""SQLAlchemy engine, session factory, and declarative Base."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all models."""
    pass


def _create_engine():
    return create_engine(
        settings.database_url,
        echo=(settings.app_env == "development"),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def _create_async_engine():
    # psycopg v3 uses the same URL prefix for sync and async engines.
    # For SQLite (tests), async requires sqlite+aiosqlite:// — but the
    # async session is not used in the test suite, so no change is needed.
    return create_async_engine(
        settings.database_url,
        echo=(settings.app_env == "development"),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# Lazy engine/session - created on first access
_engine = None
_session_local = None
_async_engine = None
_async_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory():
    global _session_local
    if _session_local is None:
        _session_local = sessionmaker(
            bind=get_engine(), autocommit=False, autoflush=False
        )
    return _session_local


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = _create_async_engine()
    return _async_engine


def get_async_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_async_engine(), expire_on_commit=False
        )
    return _async_session_factory


# Convenience aliases for production code
def SessionLocal():
    return get_session_factory()()


def get_db():
    """FastAPI dependency that yields a synchronous DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """FastAPI dependency yielding an AsyncSession (psycopg v3 native async)."""
    async with get_async_session_factory()() as session:
        yield session
