"""CISA Known Exploited Vulnerabilities (KEV) adapter.

Source: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
No API key required. Single JSON file with full catalog.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.services.ingestion.base_adapter import BaseAdapter, RawAlertData

logger = logging.getLogger(__name__)

CISA_KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/"
    "known_exploited_vulnerabilities.json"
)
DEFAULT_LOOKBACK_DAYS = 7


class CISAKEVAdapter(BaseAdapter):
    """Adapter for CISA Known Exploited Vulnerabilities catalog."""

    SOURCE_NAME = "CISA_KEV"
    SOURCE_TYPE = "api"
    BASE_URL = CISA_KEV_URL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    )
    async def _fetch_catalog(
        self, client: httpx.AsyncClient
    ) -> dict:
        """Fetch the full KEV catalog JSON."""
        resp = await client.get(CISA_KEV_URL, timeout=60.0)
        resp.raise_for_status()
        return resp.json()

    async def fetch_alerts(
        self, since: datetime | None = None
    ) -> list[RawAlertData]:
        """Fetch KEV entries added since `since` (default: last 7 days).

        CISA KEV is a single JSON file with the full catalog.
        We filter by dateAdded to get only recent entries.
        """
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(
                days=DEFAULT_LOOKBACK_DAYS
            )

        since_date = since.date() if hasattr(since, "date") else since

        alerts: list[RawAlertData] = []

        async with httpx.AsyncClient() as client:
            try:
                catalog = await self._fetch_catalog(client)
            except Exception as exc:
                logger.error("[CISA_KEV] Catalog fetch failed: %s", exc)
                return alerts

            vulnerabilities = catalog.get("vulnerabilities", [])

            for vuln in vulnerabilities:
                date_added_str = vuln.get("dateAdded", "")
                try:
                    date_added = datetime.strptime(
                        date_added_str, "%Y-%m-%d"
                    ).date()
                except (ValueError, TypeError):
                    continue

                if date_added >= since_date:
                    cve_id = vuln.get("cveID", "UNKNOWN")
                    alerts.append(
                        RawAlertData(
                            external_id=cve_id,
                            raw_data=vuln,
                            source_name=self.SOURCE_NAME,
                        )
                    )

        self._log_fetch(len(alerts))
        return alerts
