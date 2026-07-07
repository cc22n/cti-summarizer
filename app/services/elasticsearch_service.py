"""Elasticsearch / Logstash alert forwarder.

Indexes normalized alerts into Elasticsearch using the REST API over httpx.
The same URL can point to a Logstash HTTP-input plugin instead of ES directly,
which then routes to any downstream SIEM (Splunk, OpenSearch, etc.).

All functions are no-ops when ELASTICSEARCH_URL is not configured.
"""

import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_NDJSON_CT = "application/x-ndjson"
_JSON_CT = "application/json"


def _base_url() -> str:
    return settings.elasticsearch_url.rstrip("/")


def _index() -> str:
    return settings.elasticsearch_index


def _alert_to_doc(alert) -> dict[str, Any]:
    return {
        "@timestamp": (
            alert.published_date.isoformat()
            if alert.published_date
            else alert.normalized_at.isoformat()
        ),
        "title": alert.title or "",
        "description": (alert.description or "")[:2000],
        "severity": alert.severity,
        "source_name": alert.source_name,
        "cvss_score": float(alert.cvss_score) if alert.cvss_score else None,
        "iocs": alert.iocs or {},
        "mitre_techniques": alert.mitre_techniques or {},
        "affected_products": alert.affected_products or {},
        "alert_id": alert.id,
    }


async def ensure_index() -> bool:
    """Create the ES index with CTI field mapping if it does not exist."""
    if not _base_url():
        return False
    mapping = {
        "mappings": {
            "properties": {
                "@timestamp": {"type": "date"},
                "title": {"type": "text"},
                "description": {"type": "text"},
                "severity": {"type": "keyword"},
                "source_name": {"type": "keyword"},
                "cvss_score": {"type": "float"},
                "alert_id": {"type": "long"},
            }
        }
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.put(
                f"{_base_url()}/{_index()}",
                headers={"Content-Type": _JSON_CT},
                content=json.dumps(mapping),
            )
            if resp.status_code not in (200, 201, 400):
                resp.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("ES ensure_index failed: %s", exc)
        return False


async def index_alert(alert) -> bool:
    """Index a single alert via the ES _doc API. Returns False on error."""
    if not _base_url():
        return False
    doc = _alert_to_doc(alert)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.put(
                f"{_base_url()}/{_index()}/_doc/{alert.id}",
                headers={"Content-Type": _JSON_CT},
                content=json.dumps(doc, default=str),
            )
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("ES index_alert(%s) failed: %s", alert.id, exc)
        return False


async def bulk_index_alerts(alerts: list) -> int:
    """Bulk-index a list of alerts using the ES _bulk API.

    Returns the number of successfully indexed documents.
    """
    if not _base_url() or not alerts:
        return 0

    lines: list[str] = []
    for alert in alerts:
        lines.append(json.dumps({"index": {"_index": _index(), "_id": str(alert.id)}}))
        lines.append(json.dumps(_alert_to_doc(alert), default=str))
    body = "\n".join(lines) + "\n"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_base_url()}/_bulk",
                headers={"Content-Type": _NDJSON_CT},
                content=body,
            )
            resp.raise_for_status()
            data = resp.json()
            errors = [
                item
                for item in data.get("items", [])
                if "error" in item.get("index", {})
            ]
            if errors:
                logger.warning("ES bulk: %d write error(s)", len(errors))
            indexed = len(data.get("items", [])) - len(errors)
            return indexed
    except Exception as exc:
        logger.warning("ES bulk_index_alerts failed: %s", exc)
        return 0
