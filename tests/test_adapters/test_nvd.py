"""Tests for NVD adapter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ingestion.nvd_adapter import NVDAdapter


NVD_MOCK_RESPONSE = {
    "resultsPerPage": 2,
    "startIndex": 0,
    "totalResults": 2,
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2026-0001",
                "descriptions": [
                    {"lang": "en", "value": "Buffer overflow in Example"}
                ],
                "metrics": {
                    "cvssMetricV31": [
                        {"cvssData": {"baseScore": 9.8, "attackVector": "NETWORK"}}
                    ]
                },
                "published": "2026-03-28T12:00:00Z",
                "references": [],
                "weaknesses": [],
                "configurations": [],
            }
        },
        {
            "cve": {
                "id": "CVE-2026-0002",
                "descriptions": [
                    {"lang": "en", "value": "SQL injection in Demo App"}
                ],
                "metrics": {},
                "published": "2026-03-29T08:00:00Z",
                "references": [],
                "weaknesses": [],
                "configurations": [],
            }
        },
    ],
}


class MockResponse:
    """Mock httpx response."""

    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                "error", request=None, response=self
            )


@pytest.mark.asyncio
async def test_nvd_fetch_alerts():
    """Test NVD adapter fetches and parses CVEs."""
    adapter = NVDAdapter()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=MockResponse(NVD_MOCK_RESPONSE))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.ingestion.nvd_adapter.httpx.AsyncClient", return_value=mock_client):
        alerts = await adapter.fetch_alerts(
            since=datetime(2026, 3, 27, tzinfo=timezone.utc)
        )

    assert len(alerts) == 2
    assert alerts[0].external_id == "CVE-2026-0001"
    assert alerts[0].source_name == "NVD"
    assert alerts[1].external_id == "CVE-2026-0002"


@pytest.mark.asyncio
async def test_nvd_empty_response():
    """Test NVD adapter handles empty response gracefully."""
    adapter = NVDAdapter()

    empty_response = {
        "resultsPerPage": 0,
        "startIndex": 0,
        "totalResults": 0,
        "vulnerabilities": [],
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=MockResponse(empty_response))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.ingestion.nvd_adapter.httpx.AsyncClient", return_value=mock_client):
        alerts = await adapter.fetch_alerts()

    assert len(alerts) == 0
