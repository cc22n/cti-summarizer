"""Shared test fixtures."""

import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.dependencies import require_api_key
from app.main import app
from app.models import (  # noqa: F401
    Source,
    RawAlert,
    NormalizedAlert,
    AlertCategory,
    IngestionLog,
    User,
)

# SQLite does not support JSONB natively. Map it to JSON for tests.
SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON

# In-memory SQLite for tests (fast, no external deps)
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)


_CACHE_KEYS = ["alerts:stats", "dashboard:overview"]


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    # Evict any cached responses so Redis state from prior tests doesn't leak
    from app import cache as _cache
    for _key in _CACHE_KEYS:
        _cache.invalidate(_key)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db():
    """Yield a test DB session."""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """FastAPI test client with overridden DB dependency and auth bypass."""

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    def _bypass_auth():
        return None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[require_api_key] = _bypass_auth
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_source(db):
    """Create a sample NVD source."""
    source = Source(
        name="NVD",
        source_type="api",
        base_url="https://services.nvd.nist.gov/rest/json/cves/2.0",
        polling_interval_minutes=360,
        is_active=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@pytest.fixture
def sample_raw_alert(db, sample_source):
    """Create a sample raw alert."""
    raw = RawAlert(
        source_id=sample_source.id,
        external_id="CVE-2026-12345",
        raw_data={
            "cve": {
                "id": "CVE-2026-12345",
                "descriptions": [
                    {"lang": "en", "value": "Test vulnerability description"}
                ],
                "metrics": {
                    "cvssMetricV31": [
                        {
                            "cvssData": {
                                "baseScore": 8.5,
                                "attackVector": "NETWORK",
                            }
                        }
                    ]
                },
                "weaknesses": [
                    {
                        "description": [
                            {"value": "CWE-79"}
                        ]
                    }
                ],
                "references": [
                    {"url": "https://example.com/advisory", "source": "vendor"}
                ],
                "published": "2026-03-15T10:00:00Z",
                "configurations": [],
            }
        },
    )
    db.add(raw)
    db.commit()
    db.refresh(raw)
    return raw


@pytest.fixture
def sample_normalized_alert(db, sample_raw_alert):
    """Create a sample normalized alert."""
    from decimal import Decimal

    alert = NormalizedAlert(
        raw_alert_id=sample_raw_alert.id,
        title="CVE-2026-12345",
        description="Test vulnerability description",
        severity="high",
        cvss_score=Decimal("8.5"),
        source_name="NVD",
        attack_vectors={"vector": "NETWORK"},
        mitre_techniques={"cwes": ["CWE-79"]},
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
