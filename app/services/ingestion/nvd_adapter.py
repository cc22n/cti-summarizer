"""NVD (NIST National Vulnerability Database) adapter.

Uses NVD API 2.0: https://services.nvd.nist.gov/rest/json/cves/2.0
Rate limits: 5 requests/30s without API key, 50 requests/30s with key.
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

from app.config import settings
from app.services.ingestion.base_adapter import BaseAdapter, RawAlertData

logger = logging.getLogger(__name__)

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEFAULT_LOOKBACK_HOURS = 24
PAGE_SIZE = 100  # NVD max resultsPerPage = 2000, we use 100 for safety


class NVDAdapter(BaseAdapter):
    """Adapter for NIST NVD CVE feed."""

    SOURCE_NAME = "NVD"
    SOURCE_TYPE = "api"
    BASE_URL = NVD_API_URL

    def __init__(self) -> None:
        self._api_key = settings.nvd_api_key or None
        self._headers: dict[str, str] = {}
        if self._api_key:
            self._headers["apiKey"] = self._api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    )
    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        params: dict,
    ) -> dict:
        """Fetch a single page from NVD API with retry logic."""
        resp = await client.get(
            NVD_API_URL, params=params, headers=self._headers, timeout=60.0
        )
        resp.raise_for_status()
        return resp.json()

    async def fetch_alerts(
        self, since: datetime | None = None
    ) -> list[RawAlertData]:
        """Fetch CVEs modified since `since` (default: last 24h).

        Paginates through results using startIndex.
        """
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(
                hours=DEFAULT_LOOKBACK_HOURS
            )

        # NVD expects ISO 8601 format
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S.000")
        now_str = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000"
        )

        alerts: list[RawAlertData] = []
        start_index = 0

        async with httpx.AsyncClient() as client:
            while True:
                params = {
                    "lastModStartDate": since_str,
                    "lastModEndDate": now_str,
                    "resultsPerPage": PAGE_SIZE,
                    "startIndex": start_index,
                }

                try:
                    data = await self._fetch_page(client, params)
                except Exception as exc:
                    logger.error("[NVD] API request failed: %s", exc)
                    break

                vulnerabilities = data.get("vulnerabilities", [])
                total_results = data.get("totalResults", 0)

                for vuln in vulnerabilities:
                    cve_data = vuln.get("cve", {})
                    cve_id = cve_data.get("id", "UNKNOWN")

                    alerts.append(
                        RawAlertData(
                            external_id=cve_id,
                            raw_data=vuln,
                            source_name=self.SOURCE_NAME,
                        )
                    )

                start_index += PAGE_SIZE
                if start_index >= total_results:
                    break

                logger.debug(
                    "[NVD] Page fetched: %d/%d", start_index, total_results
                )

        self._log_fetch(len(alerts))
        return alerts
