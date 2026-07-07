"""MITRE ATT&CK adapter.

Fetches the enterprise ATT&CK STIX bundle from GitHub and extracts
attack-pattern (technique) objects modified since `since`.

Source: https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json
No API key required. Bundle is ~40MB; filtered to ~600 techniques.
ETag caching avoids re-downloading unchanged bundles (7-day TTL in Redis).
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

MITRE_BUNDLE_URL = (
    "https://raw.githubusercontent.com/mitre/cti/master/"
    "enterprise-attack/enterprise-attack.json"
)
DEFAULT_LOOKBACK_DAYS = 30
_ETAG_CACHE_KEY = "mitre:bundle:etag"
_ETAG_TTL = 7 * 24 * 3600  # 7 days in seconds


class MITREAdapter(BaseAdapter):
    """Adapter for MITRE ATT&CK enterprise techniques."""

    SOURCE_NAME = "MITRE_ATTACK"
    SOURCE_TYPE = "stix"
    BASE_URL = MITRE_BUNDLE_URL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=10, max=60),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    )
    async def _fetch_bundle(self, client: httpx.AsyncClient) -> dict | None:
        """Download the STIX bundle.

        Sends If-None-Match header when a cached ETag exists. Returns None on
        304 (bundle unchanged), or the parsed JSON dict on 200.
        """
        from app import cache

        headers: dict[str, str] = {}
        etag = cache.get_cached(_ETAG_CACHE_KEY)
        if etag:
            headers["If-None-Match"] = etag
            logger.debug("[MITRE] Sending ETag: %s", etag)

        resp = await client.get(MITRE_BUNDLE_URL, timeout=120.0, headers=headers)

        if resp.status_code == 304:
            logger.info("[MITRE] Bundle unchanged (304) - skipping")
            return None

        resp.raise_for_status()

        new_etag = resp.headers.get("etag")
        if new_etag:
            cache.set_cached(_ETAG_CACHE_KEY, new_etag, ttl=_ETAG_TTL)
            logger.debug("[MITRE] Cached new ETag: %s", new_etag)

        return resp.json()

    async def fetch_alerts(
        self, since: datetime | None = None
    ) -> list[RawAlertData]:
        """Extract ATT&CK techniques modified since `since`.

        Downloads the full STIX bundle (or skips if ETag matches), then filters by:
        - type == "attack-pattern" (techniques only)
        - x_mitre_deprecated != True
        - revoked != True
        - modified >= since
        """
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(
                days=DEFAULT_LOOKBACK_DAYS
            )

        alerts: list[RawAlertData] = []

        async with httpx.AsyncClient() as client:
            try:
                bundle = await self._fetch_bundle(client)
            except Exception as exc:
                logger.error("[MITRE] Bundle fetch failed: %s", exc)
                return alerts

        if bundle is None:
            # 304 - bundle unchanged, no new techniques
            return alerts

        objects = bundle.get("objects", [])
        logger.debug("[MITRE] Bundle has %d STIX objects", len(objects))

        for obj in objects:
            if obj.get("type") != "attack-pattern":
                continue
            if obj.get("x_mitre_deprecated") or obj.get("revoked"):
                continue

            modified_str = obj.get("modified", "")
            if not modified_str:
                continue

            try:
                modified_dt = datetime.fromisoformat(
                    modified_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                continue

            if modified_dt < since:
                continue

            # Extract ATT&CK technique ID from external_references
            technique_id = self._extract_technique_id(obj)
            if not technique_id:
                technique_id = obj.get("id", "unknown")

            alerts.append(
                RawAlertData(
                    external_id=technique_id,
                    raw_data=obj,
                    source_name=self.SOURCE_NAME,
                )
            )

        self._log_fetch(len(alerts))
        return alerts

    @staticmethod
    def _extract_technique_id(obj: dict) -> str | None:
        """Extract the ATT&CK technique ID (e.g. T1059.001) from STIX object."""
        for ref in obj.get("external_references", []):
            if ref.get("source_name") == "mitre-attack":
                return ref.get("external_id")
        return None
