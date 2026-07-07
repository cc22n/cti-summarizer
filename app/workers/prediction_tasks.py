"""Celery task for threat trend predictions."""

import logging

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.prediction_service import run_predictions

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="run_prediction_task",
    max_retries=1,
    time_limit=3600,       # hard kill after 1 hour
    soft_time_limit=3000,  # SoftTimeLimitExceeded raised at 50 min
)
def run_prediction_task(self):
    """Generate Prophet predictions for the next 14 days.

    Scheduled weekly via Celery Beat.
    Can also be triggered on demand via POST /api/v1/predictions/generate.
    """
    db = SessionLocal()
    try:
        result = run_predictions(db)
        logger.info("[run_prediction_task] %s", result)
        return result
    except Exception as exc:
        db.rollback()
        logger.error("[run_prediction_task] failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()
