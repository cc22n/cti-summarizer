"""Tests for the VirusTotal adapter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion.virustotal_adapter import VirusTotalAdapter


def _recent_ts() -> int:
    return int(datetime(2026, 6, 20, tzinfo=timezone.utc).timestamp())


def _make_vt_item(sha256: str = "abc123", last_submission: int | None = None):
    return {
        "id": sha256,
        "attributes": {
            "sha256": sha256,
            "meaningful_name": f"malware_{sha256}.exe",
            "last_submission_date": last_submission if last_submission is not None else _recent_ts(),
            "last_analysis_stats": {"malicious": 15, "undetected": 5},
            "tags": ["malware"],
        },
    }


def _mock_http_client(status_code: int, data: list | None = None):
    response_body = {"data": data or []}
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = response_body
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestVirusTotalAdapter:
    def test_no_api_key_fetch_returns_empty(self):
        adapter = VirusTotalAdapter()
        adapter._api_key = ""

        import asyncio
        results = asyncio.get_event_loop().run_until_complete(adapter.fetch_alerts())
        assert results == []

    @pytest.mark.asyncio
    async def test_403_response_returns_empty(self):
        adapter = VirusTotalAdapter()
        adapter._api_key = "fake-key"

        with patch(
            "app.services.ingestion.virustotal_adapter.httpx.AsyncClient",
            return_value=_mock_http_client(403),
        ):
            results = await adapter.fetch_alerts()

        assert results == []

    @pytest.mark.asyncio
    async def test_successful_fetch_returns_raw_alert_data(self):
        adapter = VirusTotalAdapter()
        adapter._api_key = "fake-key"

        # Pass an explicit since older than the mock items so none are filtered out
        since = datetime(2026, 6, 1, tzinfo=timezone.utc)
        items = [_make_vt_item("sha256abc"), _make_vt_item("sha256def")]
        with patch(
            "app.services.ingestion.virustotal_adapter.httpx.AsyncClient",
            return_value=_mock_http_client(200, items),
        ):
            results = await adapter.fetch_alerts(since=since)

        assert len(results) == 2
        assert results[0].external_id == "vt-sha256abc"
        assert results[0].source_name == "VirusTotal"

    @pytest.mark.asyncio
    async def test_since_filter_excludes_old_submissions(self):
        adapter = VirusTotalAdapter()
        adapter._api_key = "fake-key"

        since = datetime(2026, 6, 15, tzinfo=timezone.utc)
        old_ts = int(datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp())
        new_ts = int(datetime(2026, 6, 20, tzinfo=timezone.utc).timestamp())
        items = [
            _make_vt_item("old-sha", last_submission=old_ts),
            _make_vt_item("new-sha", last_submission=new_ts),
        ]
        with patch(
            "app.services.ingestion.virustotal_adapter.httpx.AsyncClient",
            return_value=_mock_http_client(200, items),
        ):
            results = await adapter.fetch_alerts(since=since)

        assert len(results) == 1
        assert results[0].external_id == "vt-new-sha"
