"""Tests for the MITRE ATT&CK adapter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion.mitre_adapter import MITREAdapter


def _make_stix_bundle(objects: list) -> dict:
    """Helper to build a minimal STIX bundle."""
    return {"type": "bundle", "id": "bundle--test", "objects": objects}


def _make_attack_pattern(
    technique_id: str,
    modified: str = "2026-03-01T00:00:00Z",
    deprecated: bool = False,
    revoked: bool = False,
) -> dict:
    """Helper to build a minimal STIX attack-pattern object."""
    obj = {
        "type": "attack-pattern",
        "id": f"attack-pattern--{technique_id}",
        "name": f"Technique {technique_id}",
        "modified": modified,
        "external_references": [
            {"source_name": "mitre-attack", "external_id": technique_id}
        ],
    }
    if deprecated:
        obj["x_mitre_deprecated"] = True
    if revoked:
        obj["revoked"] = True
    return obj


@pytest.fixture
def adapter():
    return MITREAdapter()


@pytest.mark.asyncio
async def test_fetch_alerts_returns_attack_patterns(adapter):
    """Fetches and returns attack-pattern objects from bundle."""
    bundle = _make_stix_bundle([
        _make_attack_pattern("T1059"),
        _make_attack_pattern("T1190"),
    ])
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = bundle

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        since = datetime(2026, 1, 1, tzinfo=timezone.utc)
        results = await adapter.fetch_alerts(since=since)

    assert len(results) == 2
    assert results[0].external_id == "T1059"
    assert results[1].external_id == "T1190"


@pytest.mark.asyncio
async def test_fetch_alerts_filters_non_attack_patterns(adapter):
    """Only attack-pattern type objects are returned."""
    bundle = _make_stix_bundle([
        _make_attack_pattern("T1059"),
        {"type": "malware", "id": "malware--abc", "modified": "2026-03-01T00:00:00Z"},
        {"type": "tool", "id": "tool--xyz", "modified": "2026-03-01T00:00:00Z"},
    ])
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = bundle

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        results = await adapter.fetch_alerts(since=datetime(2026, 1, 1, tzinfo=timezone.utc))

    assert len(results) == 1
    assert results[0].external_id == "T1059"


@pytest.mark.asyncio
async def test_fetch_alerts_skips_deprecated_and_revoked(adapter):
    """Deprecated and revoked techniques are excluded."""
    bundle = _make_stix_bundle([
        _make_attack_pattern("T1059"),
        _make_attack_pattern("T1234", deprecated=True),
        _make_attack_pattern("T1567", revoked=True),
    ])
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = bundle

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        results = await adapter.fetch_alerts(since=datetime(2026, 1, 1, tzinfo=timezone.utc))

    assert len(results) == 1
    assert results[0].external_id == "T1059"


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
async def test_fetch_alerts_empty_bundle(adapter):
    """Empty bundle returns empty list without errors."""
    bundle = _make_stix_bundle([])
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = bundle

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        results = await adapter.fetch_alerts()

    assert results == []
