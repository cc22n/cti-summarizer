"""VirusTotal Intelligence feed adapter.

Fetches recently-detected high-confidence threats from the VirusTotal
Intelligence Search API.

Requires VIRUSTOTAL_API_KEY with VT Intelligence access.
On free-tier keys (403) the adapter returns an empty list with a warning.
Rate limit for free tier: 4 requests/minute; Intelligence: higher limits.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.ingestion.base_adapter import BaseAdapter, RawAlertData

logger = logging.getLogger(__name__)

_VT_BASE = "https://www.virustotal.com/api/v3"
_SEARCH_URL = f"{_VT_BASE}/intelligence/search"
_DEFAULT_QUERY = "positives:10+ tag:malware"
_CAP = 100


class VirusTotalAdapter(BaseAdapter):
    """Fetches recent high-confidence malware indicators from VirusTotal.

    Uses the VT Intelligence Search endpoint. The default query targets
    files with 10+ AV detections tagged as malware. Configure a different
    query via VT_SEARCH_QUERY in .env.
    """

    SOURCE_NAME = "VirusTotal"
    SOURCE_TYPE = "api"
    BASE_URL = _VT_BASE

    def __init__(self) -> None:
        from app.config import settings

        self._api_key: str = settings.virustotal_api_key
        self._search_query: str = getattr(
            settings, "vt_search_query", _DEFAULT_QUERY
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        reraise=True,
    )
    async def _search(
        self, client: httpx.AsyncClient, order_by: str = "last_submission_date-"
    ) -> list[dict]:
        """Run VT intelligence search and return raw file objects."""
        resp = await client.get(
            _SEARCH_URL,
            params={
                "query": self._search_query,
                "limit": _CAP,
                "order": order_by,
                "attributes": "sha256,meaningful_name,last_submission_date,last_analysis_stats,tags",
            },
            headers={"x-apikey": self._api_key},
            timeout=30.0,
        )

        if resp.status_code == 403:
            logger.warning(
                "[VT] Intelligence Search returned 403 - "
                "API key may lack VT Intelligence access. Skipping."
            )
            return []
        if resp.status_code == 401:
            logger.warning("[VT] Invalid API key (401). Skipping.")
            return []

        resp.raise_for_status()
        return resp.json().get("data", [])

    async def fetch_alerts(
        self, since: datetime | None = None
    ) -> list[RawAlertData]:
        """Return recent malware samples detected since `since`."""
        if not self._api_key:
            logger.warning("[VT] VIRUSTOTAL_API_KEY not set - skipping.")
            return []

        if since is None:
            since = datetime.now(timezone.utc) - timedelta(days=1)

        results: list[RawAlertData] = []

        async with httpx.AsyncClient() as client:
            try:
                items = await self._search(client)
            except Exception as exc:
                logger.error("[VT] Search failed: %s", exc)
                return results

        for item in items:
            attrs = item.get("attributes", {})
            sha256 = attrs.get("sha256") or item.get("id", "")
            if not sha256:
                continue

            last_submission = attrs.get("last_submission_date")
            if last_submission:
                try:
                    submitted_at = datetime.fromtimestamp(
                        last_submission, tz=timezone.utc
                    )
                    if submitted_at <= since:
                        continue
                except (OSError, OverflowError, ValueError):
                    pass

            results.append(
                RawAlertData(
                    external_id=f"vt-{sha256}",
                    raw_data=item,
                    source_name=self.SOURCE_NAME,
                )
            )

        self._log_fetch(len(results))
        return results
