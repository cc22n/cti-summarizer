"""Tests for the AlienVault OTX adapter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion.otx_adapter import OTXAdapter


def _make_pulse(pulse_id: str, indicator_count: int = 5, tags: list | None = None):
    """Helper to build a minimal OTX pulse dict."""
    return {
        "id": pulse_id,
        "name": f"Pulse {pulse_id}",
        "description": "Test pulse",
        "indicator_count": indicator_count,
        "tags": tags or [],
        "modified": "2026-04-01T00:00:00",
    }


@pytest.fixture
def adapter():
    """OTX adapter with a fake API key."""
    with patch("app.services.ingestion.otx_adapter.settings") as mock_settings:
        mock_settings.otx_api_key = "fake-test-key"
        yield OTXAdapter()


@pytest.mark.asyncio
async def test_fetch_alerts_returns_raw_alert_data(adapter):
    """Successful fetch returns one RawAlertData per pulse."""
    page_data = {
        "results": [_make_pulse("pulse-001"), _make_pulse("pulse-002")],
        "next": None,
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = page_data

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        results = await adapter.fetch_alerts()

    assert len(results) == 2
    assert results[0].external_id == "pulse-001"
    assert results[1].external_id == "pulse-002"
    assert results[0].source_name == "OTX"


@pytest.mark.asyncio
async def test_fetch_alerts_returns_empty_on_http_error(adapter):
    """HTTP error does not raise; returns empty list."""
    import httpx

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
        mock_client_cls.return_value = mock_client

        results = await adapter.fetch_alerts()

    assert results == []


@pytest.mark.asyncio
async def test_fetch_alerts_paginates(adapter):
    """Adapter follows pagination until next is None."""
    page1 = {
        "results": [_make_pulse("p-1"), _make_pulse("p-2")],
        "next": "https://otx.alienvault.com/?page=2",
    }
    page2 = {
        "results": [_make_pulse("p-3")],
        "next": None,
    }

    responses = [page1, page2]
    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = responses[call_count]
        call_count += 1
        return resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get
        mock_client_cls.return_value = mock_client

        results = await adapter.fetch_alerts()

    assert len(results) == 3
    assert {r.external_id for r in results} == {"p-1", "p-2", "p-3"}


@pytest.mark.asyncio
async def test_fetch_alerts_skips_no_api_key():
    """Without API key, returns empty list and logs warning."""
    with patch("app.services.ingestion.otx_adapter.settings") as mock_settings:
        mock_settings.otx_api_key = ""
        adapter = OTXAdapter()
        results = await adapter.fetch_alerts()

    assert results == []


@pytest.mark.asyncio
async def test_x_otx_api_key_header_sent(adapter):
    """Adapter sends the X-OTX-API-KEY header in every request."""
    page_data = {"results": [], "next": None}
    captured_headers = {}

    async def mock_get(*args, **kwargs):
        captured_headers.update(kwargs.get("headers", {}))
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = page_data
        return resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get
        mock_client_cls.return_value = mock_client

        await adapter.fetch_alerts()

    assert "X-OTX-API-KEY" in captured_headers
    assert captured_headers["X-OTX-API-KEY"] == "fake-test-key"
