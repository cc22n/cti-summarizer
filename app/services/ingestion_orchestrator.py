"""Ingestion orchestrator - coordinates the full ingestion pipeline.

Flow: Adapter.fetch_alerts() -> store RawAlerts -> normalize -> assign categories
      -> store NormalizedAlerts -> notify critical/high -> log result
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import cache
from app.models.alert import NormalizedAlert, RawAlert
from app.models.category import AlertCategory
from app.models.ingestion_log import IngestionLog
from app.models.source import Source
from app.services.ingestion.base_adapter import BaseAdapter, IngestionResult
from app.services.normalization import NormalizationService
from app.services.notification_service import send_webhook

logger = logging.getLogger(__name__)

_CONSECUTIVE_FAILURE_THRESHOLD = 3


class IngestionOrchestrator:
    """Runs the full ingestion + normalization pipeline for a source."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.normalizer = NormalizationService()

    async def run(self, adapter: BaseAdapter) -> IngestionResult:
        """Execute full pipeline for a given adapter.

        1. Ensure source exists in DB
        2. Fetch raw alerts via adapter
        3. Deduplicate against existing raw_alerts
        4. Store new raw alerts
        5. Normalize each new raw alert + assign categories
        6. Notify on new critical/high alerts
        7. Log ingestion result
        8. Alert on consecutive ingestion failures
        """
        result = IngestionResult(
            source_name=adapter.SOURCE_NAME,
            status="success",
            started_at=datetime.now(timezone.utc),
        )

        # 1. Ensure source record exists
        source = self._ensure_source(adapter)

        # Load categories once for the entire run
        categories = self.db.query(AlertCategory).all()

        try:
            # 2. Fetch from adapter
            raw_alerts_data = await adapter.fetch_alerts(
                since=source.last_polled_at
            )
            result.alerts_fetched = len(raw_alerts_data)

            # 3-4. Deduplicate and store.
            # Query only the IDs present in this batch (bounded by batch size,
            # not by total historical alerts for the source).  The DB-level
            # unique constraint uq_raw_alerts_source_external acts as a safety
            # net for any concurrent workers that slip past this in-process check.
            batch_external_ids = [ad.external_id for ad in raw_alerts_data]
            existing_ids: set[str] = set()
            if batch_external_ids:
                existing_ids = {
                    row[0]
                    for row in self.db.query(RawAlert.external_id)
                    .filter(
                        RawAlert.source_id == source.id,
                        RawAlert.external_id.in_(batch_external_ids),
                    )
                    .all()
                }

            new_normalized: list[NormalizedAlert] = []
            new_count = 0

            for alert_data in raw_alerts_data:
                if alert_data.external_id in existing_ids:
                    continue

                existing_ids.add(alert_data.external_id)
                raw_alert = RawAlert(
                    source_id=source.id,
                    external_id=alert_data.external_id,
                    raw_data=alert_data.raw_data,
                )
                self.db.add(raw_alert)
                self.db.flush()  # get raw_alert.id

                # 5. Normalize + assign categories
                normalized = self.normalizer.normalize_raw_alert(
                    raw_alert, self.db
                )
                if normalized:
                    self.db.add(normalized)
                    self.db.flush()  # get normalized.id for M2M relationship
                    NormalizationService.assign_categories(normalized, categories)
                    raw_alert.is_processed = True
                    new_normalized.append(normalized)

                new_count += 1

            result.alerts_new = new_count

            # Update source polling timestamp
            source.last_polled_at = datetime.now(timezone.utc)
            self.db.commit()

            # 6. Notify on new critical/high alerts
            critical_high = [
                n for n in new_normalized
                if n.severity in ("critical", "high")
            ]
            if critical_high:
                payload = {
                    "event": "new_critical_alerts",
                    "source": adapter.SOURCE_NAME,
                    "count": len(critical_high),
                    "alerts": [
                        {"id": n.id, "title": n.title, "severity": n.severity}
                        for n in critical_high[:5]
                    ],
                }
                await send_webhook(payload)
                # Publish to Redis Pub/Sub for WebSocket clients
                try:
                    r = cache._client()
                    if r is not None:
                        # run_in_executor avoids blocking the async event loop
                        # with the synchronous redis-py publish call.
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(
                            None, r.publish, "channel:alerts:new", json.dumps(payload)
                        )
                except Exception as _pub_exc:
                    logger.debug("[ws] Pub/Sub publish failed: %s", _pub_exc)

        except Exception as exc:
            self.db.rollback()
            result.status = "error"
            result.error_message = str(exc)
            logger.error(
                "[%s] Ingestion failed: %s", adapter.SOURCE_NAME, exc
            )

        result.completed_at = datetime.now(timezone.utc)

        # 7. Log result
        self._log_ingestion(source, result)

        logger.info(
            "[%s] Ingestion complete: fetched=%d new=%d status=%s",
            adapter.SOURCE_NAME,
            result.alerts_fetched,
            result.alerts_new,
            result.status,
        )

        # 8. Alert on consecutive failures
        if result.status == "error":
            await self._notify_if_failure_streak(source)

        return result

    def _ensure_source(self, adapter: BaseAdapter) -> Source:
        """Get or create the Source record for this adapter."""
        source = (
            self.db.query(Source)
            .filter(Source.name == adapter.SOURCE_NAME)
            .first()
        )
        if not source:
            source = Source(
                name=adapter.SOURCE_NAME,
                source_type=adapter.SOURCE_TYPE,
                base_url=adapter.BASE_URL,
                is_active=True,
            )
            self.db.add(source)
            self.db.flush()
            logger.info("Created source: %s", adapter.SOURCE_NAME)
        return source

    def _log_ingestion(
        self, source: Source, result: IngestionResult
    ) -> None:
        """Write ingestion log entry."""
        log = IngestionLog(
            source_id=source.id,
            status=result.status,
            alerts_fetched=result.alerts_fetched,
            alerts_new=result.alerts_new,
            error_message=result.error_message,
            started_at=result.started_at,
            completed_at=result.completed_at,
        )
        self.db.add(log)
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.error(
                "[%s] Failed to write ingestion log: %s",
                result.source_name,
                exc,
            )

    async def _notify_if_failure_streak(self, source: Source) -> None:
        """Send a webhook if the last N consecutive ingestion logs are errors."""
        recent = (
            self.db.query(IngestionLog.status)
            .filter(IngestionLog.source_id == source.id)
            .order_by(IngestionLog.started_at.desc())
            .limit(_CONSECUTIVE_FAILURE_THRESHOLD)
            .all()
        )
        n = _CONSECUTIVE_FAILURE_THRESHOLD
        if len(recent) >= n and all(log.status == "error" for log in recent):
            await send_webhook({
                "event": "ingestion_failure_streak",
                "source": source.name,
                "consecutive_failures": n,
            })
            logger.warning(
                "[%s] %d consecutive ingestion failures - webhook sent",
                source.name,
                n,
            )
