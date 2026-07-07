"""Tests for the URLhaus adapter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion.urlhaus_adapter import URLhausAdapter


def _make_entry(url_id: str = "123", date_added: str = "2026-06-01 12:00:00 UTC"):
    return {
        "id": url_id,
        "url": f"http://malicious-{url_id}.example.com/payload",
        "url_status": "online",
        "date_added": date_added,
        "threat": "malware_download",
    }


def _mock_http_client(response_data: dict):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = response_data
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestURLhausAdapter:
    @pytest.mark.asyncio
    async def test_fetch_alerts_returns_raw_alert_data(self):
        adapter = URLhausAdapter()
        response = {
            "query_status": "is_listed",
            "urls": [_make_entry("1"), _make_entry("2")],
        }
        with patch(
            "app.services.ingestion.urlhaus_adapter.httpx.AsyncClient",
            return_value=_mock_http_client(response),
        ):
            results = await adapter.fetch_alerts()

        assert len(results) == 2
        assert results[0].external_id == "urlhaus-1"
        assert results[1].external_id == "urlhaus-2"
        assert results[0].source_name == "URLhaus"

    @pytest.mark.asyncio
    async def test_since_filter_excludes_old_entries(self):
        adapter = URLhausAdapter()
        since = datetime(2026, 6, 15, tzinfo=timezone.utc)
        response = {
            "query_status": "is_listed",
            "urls": [
                _make_entry("old", "2026-06-01 00:00:00 UTC"),
                _make_entry("new", "2026-06-20 00:00:00 UTC"),
            ],
        }
        with patch(
            "app.services.ingestion.urlhaus_adapter.httpx.AsyncClient",
            return_value=_mock_http_client(response),
        ):
            results = await adapter.fetch_alerts(since=since)

        assert len(results) == 1
        assert results[0].external_id == "urlhaus-new"

    @pytest.mark.asyncio
    async def test_entry_without_id_is_skipped(self):
        adapter = URLhausAdapter()
        response = {
            "query_status": "is_listed",
            "urls": [{"url": "http://evil.com", "date_added": "2026-06-01 00:00:00 UTC"}],
        }
        with patch(
            "app.services.ingestion.urlhaus_adapter.httpx.AsyncClient",
            return_value=_mock_http_client(response),
        ):
            results = await adapter.fetch_alerts()

        assert results == []

    @pytest.mark.asyncio
    async def test_empty_urls_list_returns_empty(self):
        adapter = URLhausAdapter()
        response = {"query_status": "ok", "urls": []}
        with patch(
            "app.services.ingestion.urlhaus_adapter.httpx.AsyncClient",
            return_value=_mock_http_client(response),
        ):
            results = await adapter.fetch_alerts()

        assert results == []
