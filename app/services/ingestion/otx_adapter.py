"""AlienVault OTX (Open Threat Exchange) adapter.

API docs: https://otx.alienvault.com/api/v1/
Endpoint: GET /api/v1/pulses/subscribed
Requires OTX_API_KEY in env.
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

OTX_BASE_URL = "https://otx.alienvault.com/api/v1"
OTX_PULSES_URL = f"{OTX_BASE_URL}/pulses/subscribed"
DEFAULT_LOOKBACK_DAYS = 7
PAGE_SIZE = 20
MAX_ALERTS = 500  # cap on first run to avoid flood


class OTXAdapter(BaseAdapter):
    """Adapter for AlienVault OTX threat intelligence pulses."""

    SOURCE_NAME = "OTX"
    SOURCE_TYPE = "api"
    BASE_URL = OTX_PULSES_URL

    def __init__(self) -> None:
        self._api_key = settings.otx_api_key or ""
        self._headers = {"X-OTX-API-KEY": self._api_key}

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
        """Fetch a single page of OTX pulses."""
        resp = await client.get(
            OTX_PULSES_URL,
            params=params,
            headers=self._headers,
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()

    async def fetch_alerts(
        self, since: datetime | None = None
    ) -> list[RawAlertData]:
        """Fetch OTX pulses modified since `since` (default: last 7 days).

        Paginates through results. Caps at MAX_ALERTS to prevent
        flood on first run when no last_polled_at exists.
        """
        if not self._api_key:
            logger.warning("[OTX] No OTX_API_KEY configured, skipping")
            return []

        if since is None:
            since = datetime.now(timezone.utc) - timedelta(
                days=DEFAULT_LOOKBACK_DAYS
            )

        since_str = since.strftime("%Y-%m-%dT%H:%M:%S.000000")
        alerts: list[RawAlertData] = []
        page = 1

        async with httpx.AsyncClient() as client:
            while len(alerts) < MAX_ALERTS:
                params = {
                    "limit": PAGE_SIZE,
                    "page": page,
                    "modified_since": since_str,
                }

                try:
                    data = await self._fetch_page(client, params)
                except Exception as exc:
                    logger.error("[OTX] API request failed: %s", exc)
                    break

                results = data.get("results", [])
                for pulse in results:
                    pulse_id = pulse.get("id", "")
                    if not pulse_id:
                        continue
                    alerts.append(
                        RawAlertData(
                            external_id=pulse_id,
                            raw_data=pulse,
                            source_name=self.SOURCE_NAME,
                        )
                    )

                # OTX returns "next" URL when more pages exist
                if not data.get("next") or not results:
                    break

                page += 1
                logger.debug("[OTX] Page %d fetched (%d total)", page, len(alerts))

        if len(alerts) >= MAX_ALERTS:
            logger.warning(
                "[OTX] Hit cap of %d alerts on this run (first run?)", MAX_ALERTS
            )

        self._log_fetch(len(alerts))
        return alerts
