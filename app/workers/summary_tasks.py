"""Celery tasks for LLM summarization and executive reports."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.alert import NormalizedAlert
from app.models.summary import Summary
from app.services.summarization_service import SummarizationService
from app.workers.utils import run_async

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="summarize_alerts", max_retries=3)
def summarize_alerts(self, alert_ids: list[int]):
    """Generate per-alert LLM summaries for the given alert IDs.

    Skips alerts that already have a summary (uq_summaries_alert_type).
    """
    db = SessionLocal()
    try:
        service = SummarizationService()
        created = 0
        skipped = 0

        # Two bulk queries replace 2N individual queries.
        already_summarised = {
            row[0]
            for row in db.query(Summary.normalized_alert_id)
            .filter(
                Summary.normalized_alert_id.in_(alert_ids),
                Summary.summary_type == "alert",
            )
            .all()
        }
        alerts_by_id = {
            a.id: a
            for a in db.query(NormalizedAlert)
            .filter(NormalizedAlert.id.in_(alert_ids))
            .all()
        }

        for alert_id in alert_ids:
            if alert_id in already_summarised:
                skipped += 1
                continue

            alert = alerts_by_id.get(alert_id)
            if not alert:
                logger.warning("Alert %d not found, skipping", alert_id)
                continue

            try:
                summary = run_async(service.summarize_alert(alert))
            except Exception as exc:
                logger.error("Summarization failed for alert %d: %s", alert_id, exc)
                raise self.retry(exc=exc, countdown=30)

            if summary:
                db.add(summary)
                created += 1

        if created > 0:
            db.commit()

        logger.info(
            "[summarize_alerts] done: created=%d skipped=%d", created, skipped
        )
        return {"created": created, "skipped": skipped}

    except Exception as exc:
        db.rollback()
        logger.error("[summarize_alerts] task failed: %s", exc)
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="generate_daily_digest", max_retries=2)
def generate_daily_digest(self, hours: int = 24):
    """Generate a digest summary for the last `hours` hours of alerts."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(hours=hours)

        # Cap at 500 alerts: the LLM context window cannot handle more,
        # and loading thousands of rows unbounded risks OOM under high volume.
        # Prioritise critical/high first so the digest covers the most
        # important alerts even when the cap is reached.
        from sqlalchemy import case as sa_case
        severity_order = sa_case(
            (NormalizedAlert.severity == "critical", 1),
            (NormalizedAlert.severity == "high", 2),
            (NormalizedAlert.severity == "medium", 3),
            (NormalizedAlert.severity == "low", 4),
            else_=5,
        )
        alerts = (
            db.query(NormalizedAlert)
            .filter(NormalizedAlert.normalized_at >= period_start)
            .order_by(severity_order, NormalizedAlert.normalized_at.desc())
            .limit(500)
            .all()
        )

        if not alerts:
            logger.info("[generate_daily_digest] No alerts in last %dh", hours)
            return {"status": "skipped", "reason": "no alerts"}

        service = SummarizationService()
        try:
            summary = run_async(
                service.generate_digest(alerts, period_start, now)
            )
        except Exception as exc:
            raise self.retry(exc=exc, countdown=60)

        if summary:
            db.add(summary)
            db.commit()
            logger.info(
                "[generate_daily_digest] Created digest covering %d alerts",
                len(alerts),
            )
            return {"status": "success", "alerts_covered": len(alerts)}

        return {"status": "failed", "reason": "LLM returned no content"}

    except Exception as exc:
        db.rollback()
        logger.error("[generate_daily_digest] task failed: %s", exc)
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="send_weekly_report", max_retries=2)
def send_weekly_report_task(self):
    """Build and email the weekly executive threat report.

    Queries the last 7 days of normalized alerts, computes stats,
    fetches the latest digest summary, and sends an HTML email.
    Skips silently when SMTP is not configured.
    """
    from app.services.email_service import send_weekly_report

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=7)

        total = (
            db.query(func.count(NormalizedAlert.id))
            .filter(NormalizedAlert.normalized_at >= period_start)
            .scalar()
            or 0
        )

        severity_rows = (
            db.query(NormalizedAlert.severity, func.count(NormalizedAlert.id))
            .filter(NormalizedAlert.normalized_at >= period_start)
            .group_by(NormalizedAlert.severity)
            .all()
        )
        by_severity = {row[0]: row[1] for row in severity_rows}

        source_rows = (
            db.query(NormalizedAlert.source_name, func.count(NormalizedAlert.id))
            .filter(NormalizedAlert.normalized_at >= period_start)
            .group_by(NormalizedAlert.source_name)
            .all()
        )
        by_source = {row[0]: row[1] for row in source_rows}

        latest_digest = (
            db.query(Summary)
            .filter(Summary.summary_type == "digest")
            .order_by(Summary.created_at.desc())
            .first()
        )
        digest_text = latest_digest.content if latest_digest else None

        stats = {
            "total": total,
            "by_severity": by_severity,
            "by_source": by_source,
            "period_start": period_start.isoformat(),
            "period_end": now.isoformat(),
        }

        sent = send_weekly_report(stats, digest_text)
        logger.info("[send_weekly_report] sent=%s total_alerts=%d", sent, total)
        return {"sent": sent, "total_alerts": total}

    except Exception as exc:
        logger.error("[send_weekly_report] failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()
