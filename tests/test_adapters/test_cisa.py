"""Tests for CISA KEV adapter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ingestion.cisa_adapter import CISAKEVAdapter


CISA_MOCK_CATALOG = {
    "title": "CISA KEV Catalog",
    "catalogVersion": "2026.03.30",
    "count": 3,
    "vulnerabilities": [
        {
            "cveID": "CVE-2026-1111",
            "vendorProject": "Microsoft",
            "product": "Exchange Server",
            "vulnerabilityName": "Microsoft Exchange RCE",
            "shortDescription": "Remote code execution in Exchange",
            "dateAdded": "2026-03-29",
            "dueDate": "2026-04-19",
            "knownRansomwareCampaignUse": "Known",
            "requiredAction": "Apply updates per vendor instructions.",
        },
        {
            "cveID": "CVE-2026-2222",
            "vendorProject": "Apache",
            "product": "Log4j",
            "vulnerabilityName": "Apache Log4j RCE",
            "shortDescription": "Remote code execution via JNDI",
            "dateAdded": "2026-03-28",
            "dueDate": "2026-04-18",
            "knownRansomwareCampaignUse": "Unknown",
            "requiredAction": "Upgrade to patched version.",
        },
        {
            "cveID": "CVE-2025-9999",
            "vendorProject": "OldVendor",
            "product": "OldProduct",
            "vulnerabilityName": "Old vulnerability",
            "shortDescription": "Should be filtered out",
            "dateAdded": "2025-01-01",
            "dueDate": "2025-02-01",
            "knownRansomwareCampaignUse": "Unknown",
            "requiredAction": "N/A",
        },
    ],
}


class MockResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


@pytest.mark.asyncio
async def test_cisa_fetch_recent():
    """Test CISA adapter fetches only recent KEV entries."""
    adapter = CISAKEVAdapter()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=MockResponse(CISA_MOCK_CATALOG))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    since = datetime(2026, 3, 27, tzinfo=timezone.utc)

    with patch("app.services.ingestion.cisa_adapter.httpx.AsyncClient", return_value=mock_client):
        alerts = await adapter.fetch_alerts(since=since)

    # Should get 2 alerts (2026-03-28 and 2026-03-29), not the old one
    assert len(alerts) == 2
    ids = {a.external_id for a in alerts}
    assert "CVE-2026-1111" in ids
    assert "CVE-2026-2222" in ids
    assert "CVE-2025-9999" not in ids


@pytest.mark.asyncio
async def test_cisa_ransomware_flag():
    """Test that ransomware campaign data is preserved."""
    adapter = CISAKEVAdapter()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=MockResponse(CISA_MOCK_CATALOG))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    since = datetime(2026, 3, 27, tzinfo=timezone.utc)

    with patch("app.services.ingestion.cisa_adapter.httpx.AsyncClient", return_value=mock_client):
        alerts = await adapter.fetch_alerts(since=since)

    exchange_alert = next(
        a for a in alerts if a.external_id == "CVE-2026-1111"
    )
    assert exchange_alert.raw_data["knownRansomwareCampaignUse"] == "Known"
