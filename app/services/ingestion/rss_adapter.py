"""Generic RSS/Atom feed adapter.

Fetches entries from one or more RSS feeds defined in settings.rss_feed_urls.
Uses feedparser (synchronous) via run_in_executor to avoid blocking the event loop.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import partial

import feedparser

from app.config import settings
from app.services.ingestion.base_adapter import BaseAdapter, RawAlertData

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_DAYS = 3


def _parse_feed(url: str) -> feedparser.FeedParserDict:
    """Synchronous feedparser call (runs in executor)."""
    return feedparser.parse(url)


def _parse_published(entry: dict) -> datetime | None:
    """Parse published date from a feedparser entry."""
    # feedparser populates published_parsed (time.struct_time) when available
    published_parsed = entry.get("published_parsed")
    if published_parsed:
        try:
            import calendar
            ts = calendar.timegm(published_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    # Fallback: parse published string
    published_str = entry.get("published", "")
    if published_str:
        try:
            # parsedate_to_datetime returns a tz-aware datetime; use astimezone
            # to convert to UTC rather than replace(), which discards the offset.
            return parsedate_to_datetime(published_str).astimezone(timezone.utc)
        except Exception:
            pass

    return None


class RSSAdapter(BaseAdapter):
    """Adapter for generic RSS/Atom CTI news feeds."""

    SOURCE_NAME = "RSS"
    SOURCE_TYPE = "rss"
    BASE_URL = "rss://multiple"  # actual URLs come from config

    async def fetch_alerts(
        self, since: datetime | None = None
    ) -> list[RawAlertData]:
        """Fetch entries from all configured RSS feeds.

        Filters by published date >= since. If a feed has no date info,
        includes all entries (feedparser normalizes most date formats).
        One bad feed does not abort the others.
        """
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(
                days=DEFAULT_LOOKBACK_DAYS
            )

        feed_urls = settings.rss_feed_urls_list
        if not feed_urls:
            logger.warning("[RSS] No RSS feed URLs configured, skipping")
            return []

        loop = asyncio.get_running_loop()
        alerts: list[RawAlertData] = []

        for url in feed_urls:
            try:
                feed = await loop.run_in_executor(None, partial(_parse_feed, url))
            except Exception as exc:
                logger.warning("[RSS] Failed to fetch %s: %s", url, exc)
                continue

            if feed.bozo and not feed.entries:
                logger.warning(
                    "[RSS] Feed parse error for %s: %s", url, feed.bozo_exception
                )
                continue

            for entry in feed.entries:
                published_dt = _parse_published(entry)
                if published_dt and published_dt < since:
                    continue

                # external_id = entry id (guid) or link
                external_id = (
                    entry.get("id") or entry.get("link") or ""
                ).strip()
                if not external_id:
                    continue

                # Store as plain dict (feedparser returns special dict subclass)
                raw = {
                    "feed_url": url,
                    "feed_title": feed.feed.get("title", ""),
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": entry.get("published", ""),
                    "tags": [
                        t.get("term", "") for t in entry.get("tags", [])
                    ],
                }

                alerts.append(
                    RawAlertData(
                        external_id=external_id,
                        raw_data=raw,
                        source_name=self.SOURCE_NAME,
                    )
                )

        self._log_fetch(len(alerts))
        return alerts
