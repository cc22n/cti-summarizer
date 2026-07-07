"""Tests for the RSS feed adapter."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.ingestion.rss_adapter import RSSAdapter


def _make_feed(entries: list, feed_title: str = "Test Feed") -> MagicMock:
    """Helper to build a minimal feedparser result."""
    feed = MagicMock()
    feed.bozo = False
    feed.entries = entries
    feed.feed = {"title": feed_title}
    return feed


def _make_entry(
    entry_id: str,
    title: str = "Test Entry",
    published: str = "Mon, 07 Apr 2026 10:00:00 GMT",
    published_parsed=None,
) -> MagicMock:
    """Helper to build a minimal feedparser entry."""
    entry = MagicMock()
    entry.get = lambda key, default="": {
        "id": entry_id,
        "title": title,
        "link": f"https://example.com/{entry_id}",
        "summary": "Entry summary",
        "published": published,
        "tags": [],
    }.get(key, default)
    entry.published_parsed = published_parsed
    return entry


@pytest.fixture
def adapter():
    """RSS adapter with a single test feed URL."""
    with patch("app.services.ingestion.rss_adapter.settings") as mock_settings:
        mock_settings.rss_feed_urls_list = ["https://example.com/feed"]
        yield RSSAdapter()


@pytest.mark.asyncio
async def test_fetch_alerts_returns_entries(adapter):
    """Successful parse returns one RawAlertData per entry."""
    entries = [_make_entry("entry-1"), _make_entry("entry-2")]
    mock_feed = _make_feed(entries)

    with patch("app.services.ingestion.rss_adapter._parse_feed", return_value=mock_feed):
        results = await adapter.fetch_alerts(
            since=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )

    assert len(results) == 2
    assert results[0].external_id == "entry-1"
    assert results[0].source_name == "RSS"


@pytest.mark.asyncio
async def test_fetch_alerts_empty_feed(adapter):
    """Feed with no entries returns empty list."""
    mock_feed = _make_feed([])

    with patch("app.services.ingestion.rss_adapter._parse_feed", return_value=mock_feed):
        results = await adapter.fetch_alerts()

    assert results == []


@pytest.mark.asyncio
async def test_fetch_alerts_skips_entry_without_id(adapter):
    """Entries with no id or link are skipped."""
    entry = MagicMock()
    entry.get = lambda key, default="": {"id": "", "link": "", "title": "no-id"}.get(key, default)
    entry.published_parsed = None
    mock_feed = _make_feed([entry])

    with patch("app.services.ingestion.rss_adapter._parse_feed", return_value=mock_feed):
        results = await adapter.fetch_alerts()

    assert results == []


@pytest.mark.asyncio
async def test_fetch_alerts_handles_feed_error(adapter):
    """Parse error on one feed does not abort; returns empty list."""
    with patch(
        "app.services.ingestion.rss_adapter._parse_feed",
        side_effect=Exception("connection refused"),
    ):
        results = await adapter.fetch_alerts()

    assert results == []


@pytest.mark.asyncio
async def test_fetch_alerts_no_feed_urls():
    """No configured feed URLs returns empty list."""
    with patch("app.services.ingestion.rss_adapter.settings") as mock_settings:
        mock_settings.rss_feed_urls_list = []
        adapter = RSSAdapter()
        results = await adapter.fetch_alerts()

    assert results == []
