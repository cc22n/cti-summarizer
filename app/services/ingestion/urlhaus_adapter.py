"""URLhaus (Abuse.ch) malicious URL feed adapter.

API: POST https://urlhaus-api.abuse.ch/v1/urls/recent/
No API key required. Returns up to 1000 recent malicious URLs.
"""

import logging
from datetime import datetime, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.ingestion.base_adapter import BaseAdapter, RawAlertData

logger = logging.getLogger(__name__)

_URLHAUS_URL = "https://urlhaus-api.abuse.ch/v1/urls/recent/"
_HIGH_RISK_THREATS = {"botnet_cc", "malware_download"}
_CAP = 500


class URLhausAdapter(BaseAdapter):
    """Fetches recent malicious URLs from URLhaus / Abuse.ch."""

    SOURCE_NAME = "URLhaus"
    SOURCE_TYPE = "api"
    BASE_URL = _URLHAUS_URL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _fetch_recent(self) -> list[dict]:
        """POST to URLhaus and return the list of URL objects."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_URLHAUS_URL)
            resp.raise_for_status()
            data = resp.json()

        query_status = data.get("query_status", "")
        if query_status not in ("is_listed", "ok"):
            logger.warning("[URLhaus] Unexpected query_status: %s", query_status)

        return data.get("urls", [])

    async def fetch_alerts(self, since: datetime | None = None) -> list[RawAlertData]:
        """Fetch recent malicious URLs, filter by date if since is provided."""
        raw_urls = await self._fetch_recent()

        results: list[RawAlertData] = []
        for entry in raw_urls[:_CAP]:
            url_id = entry.get("id")
            if not url_id:
                continue

            # Parse date_added: "YYYY-MM-DD HH:MM:SS UTC"
            date_added_str = entry.get("date_added", "")
            date_added: datetime | None = None
            if date_added_str:
                try:
                    date_added = datetime.strptime(
                        date_added_str, "%Y-%m-%d %H:%M:%S UTC"
                    ).replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

            # Filter by since if provided
            if since and date_added and date_added <= since:
                continue

            results.append(
                RawAlertData(
                    external_id=f"urlhaus-{url_id}",
                    raw_data=entry,
                    source_name=self.SOURCE_NAME,
                )
            )

        logger.info(
            "[URLhaus] Fetched %d URLs (after filter: %d)",
            len(raw_urls),
            len(results),
        )
        return results
