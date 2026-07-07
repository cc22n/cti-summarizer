"""Celery tasks for Elasticsearch / Logstash event forwarding."""

import logging
from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app
from app.workers.utils import run_async

logger = logging.getLogger(__name__)


@celery_app.task(name="forward_to_elasticsearch", max_retries=2)
def forward_to_elasticsearch_task(lookback_hours: int = 2) -> dict:
    """Index alerts from the last N hours into Elasticsearch or Logstash.

    No-op when ELASTICSEARCH_URL is not configured.
    """
    return run_async(_forward(lookback_hours))


async def _forward(lookback_hours: int) -> dict:
    from app.database import SessionLocal
    from app.models.alert import NormalizedAlert
    from app.services.elasticsearch_service import (
        bulk_index_alerts,
        ensure_index,
    )

    from app.config import settings
    if not settings.elasticsearch_url:
        return {"skipped": True, "reason": "ELASTICSEARCH_URL not configured"}

    await ensure_index()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    db = SessionLocal()
    try:
        alerts = (
            db.query(NormalizedAlert)
            .filter(NormalizedAlert.normalized_at >= cutoff)
            .order_by(NormalizedAlert.normalized_at.desc())
            .limit(1000)
            .all()
        )
    finally:
        db.close()

    indexed = await bulk_index_alerts(alerts)
    logger.info("ES forward: %d / %d alerts indexed", indexed, len(alerts))
    return {"indexed": indexed, "total": len(alerts), "lookback_hours": lookback_hours}
