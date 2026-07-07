"""Tests for the ingestion orchestrator."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.alert import NormalizedAlert, RawAlert
from app.models.ingestion_log import IngestionLog
from app.models.source import Source
from app.services.ingestion.base_adapter import BaseAdapter, RawAlertData
from app.services.ingestion_orchestrator import IngestionOrchestrator


def _make_raw_alert_data(external_id: str) -> RawAlertData:
    return RawAlertData(
        external_id=external_id,
        raw_data={"id": external_id},
        source_name="TEST",
    )


class FakeAdapter(BaseAdapter):
    """Minimal adapter for testing."""

    SOURCE_NAME = "TEST"
    SOURCE_TYPE = "api"
    BASE_URL = "https://test.example.com"

    def __init__(self, alerts: list[RawAlertData] | None = None):
        self._alerts = alerts or []

    async def fetch_alerts(self, since=None) -> list[RawAlertData]:
        return self._alerts


@pytest.fixture
def orchestrator(db):
    return IngestionOrchestrator(db)


@pytest.mark.asyncio
async def test_new_alerts_are_stored(orchestrator, db):
    """New alerts from adapter are stored as RawAlert and NormalizedAlert."""
    adapter = FakeAdapter([_make_raw_alert_data("ext-001")])

    def _fake_normalize(raw_alert, db):
        return NormalizedAlert(
            raw_alert_id=raw_alert.id,
            title="Test",
            severity="low",
            source_name="TEST",
        )

    with patch.object(orchestrator.normalizer, "normalize_raw_alert", side_effect=_fake_normalize):
        result = await orchestrator.run(adapter)

    assert result.alerts_new == 1
    assert result.status == "success"
    assert db.query(RawAlert).count() == 1


@pytest.mark.asyncio
async def test_duplicate_alerts_are_skipped(orchestrator, db):
    """Alerts with same external_id are not re-stored."""
    source = Source(
        name="TEST", source_type="api", base_url="https://test.example.com"
    )
    db.add(source)
    db.flush()

    existing_raw = RawAlert(
        source_id=source.id,
        external_id="ext-dup",
        raw_data={"id": "ext-dup"},
    )
    db.add(existing_raw)
    db.commit()

    adapter = FakeAdapter([_make_raw_alert_data("ext-dup")])

    with patch.object(
        orchestrator.normalizer, "normalize_raw_alert", return_value=None
    ):
        result = await orchestrator.run(adapter)

    assert result.alerts_new == 0
    assert db.query(RawAlert).count() == 1


@pytest.mark.asyncio
async def test_ingestion_log_is_created(orchestrator, db):
    """IngestionLog record is created after run."""
    adapter = FakeAdapter([])

    await orchestrator.run(adapter)

    logs = db.query(IngestionLog).all()
    assert len(logs) == 1
    assert logs[0].status == "success"


@pytest.mark.asyncio
async def test_source_last_polled_at_is_updated(orchestrator, db):
    """Source.last_polled_at is set after successful run."""
    adapter = FakeAdapter([])

    before = datetime.now(timezone.utc)
    await orchestrator.run(adapter)
    after = datetime.now(timezone.utc)

    source = db.query(Source).filter(Source.name == "TEST").first()
    assert source is not None
    assert source.last_polled_at is not None
    # SQLite returns naive datetimes for timezone columns; normalize before comparing.
    polled = source.last_polled_at
    if polled.tzinfo is None:
        polled = polled.replace(tzinfo=timezone.utc)
    assert before <= polled <= after


@pytest.mark.asyncio
async def test_adapter_failure_is_caught(orchestrator, db):
    """Adapter exceptions are caught; result status is error, no exception propagates."""
    class FailingAdapter(FakeAdapter):
        async def fetch_alerts(self, since=None):
            raise RuntimeError("API is down")

    adapter = FailingAdapter()
    result = await orchestrator.run(adapter)

    assert result.status == "error"
    assert "API is down" in (result.error_message or "")
