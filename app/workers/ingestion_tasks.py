"""Celery tasks for CTI feed ingestion."""

import logging

from celery.schedules import crontab

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.ingestion import (
    NVDAdapter,
    CISAKEVAdapter,
    OTXAdapter,
    MITREAdapter,
    RSSAdapter,
    URLhausAdapter,
    VirusTotalAdapter,
)
from app.services.ingestion_orchestrator import IngestionOrchestrator
from app.workers.utils import run_async

logger = logging.getLogger(__name__)

ADAPTERS = {
    "nvd": NVDAdapter,
    "cisa_kev": CISAKEVAdapter,
    "otx": OTXAdapter,
    "mitre_attack": MITREAdapter,
    "rss": RSSAdapter,
    "urlhaus": URLhausAdapter,
    "virustotal": VirusTotalAdapter,
}


@celery_app.task(
    bind=True,
    name="ingest_source",
    max_retries=2,
    time_limit=1800,       # hard kill after 30 min (MITRE downloads ~40 MB)
    soft_time_limit=1500,  # SoftTimeLimitExceeded at 25 min
)
def ingest_source(self, source_key: str):
    """Ingest alerts from a single CTI source.

    Args:
        source_key: Key from ADAPTERS dict (e.g., 'nvd', 'cisa_kev')
    """
    adapter_cls = ADAPTERS.get(source_key)
    if not adapter_cls:
        logger.error("Unknown source key: %s", source_key)
        return {"error": f"Unknown source: {source_key}"}

    db = SessionLocal()
    try:
        orchestrator = IngestionOrchestrator(db)
        adapter = adapter_cls()
        result = run_async(orchestrator.run(adapter))
        return {
            "source": result.source_name,
            "status": result.status,
            "fetched": result.alerts_fetched,
            "new": result.alerts_new,
            "error": result.error_message,
        }
    except Exception as exc:
        logger.error("Task ingest_source(%s) failed: %s", source_key, exc)
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(name="ingest_all_sources")
def ingest_all_sources():
    """Ingest from all registered CTI sources."""
    results = {}
    for key in ADAPTERS:
        task_result = ingest_source.delay(key)
        results[key] = task_result.id
    return results


# Celery Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    "ingest-nvd-every-6h": {
        "task": "ingest_source",
        "schedule": crontab(minute=0, hour="0,6,12,18"),
        "args": ("nvd",),
    },
    "ingest-cisa-kev-daily": {
        "task": "ingest_source",
        "schedule": crontab(minute=0, hour=7),
        "args": ("cisa_kev",),
    },
    "ingest-otx-every-6h": {
        "task": "ingest_source",
        "schedule": crontab(minute=30, hour="1,7,13,19"),
        "args": ("otx",),
    },
    "ingest-mitre-weekly": {
        "task": "ingest_source",
        "schedule": crontab(minute=0, hour=2, day_of_week=1),
        "args": ("mitre_attack",),
    },
    "ingest-rss-every-2h": {
        "task": "ingest_source",
        "schedule": crontab(minute=0, hour="*/2"),
        "args": ("rss",),
    },
    "ingest-urlhaus-every-4h": {
        "task": "ingest_source",
        "schedule": crontab(minute=0, hour="2,6,10,14,18,22"),
        "args": ("urlhaus",),
    },
    "generate-daily-digest": {
        "task": "generate_daily_digest",
        "schedule": crontab(minute=0, hour=8),
    },
    "predict-trends-weekly": {
        "task": "run_prediction_task",
        "schedule": crontab(minute=0, hour=3, day_of_week=1),
    },
    "ingest-virustotal-daily": {
        "task": "ingest_source",
        "schedule": crontab(minute=30, hour=4),
        "args": ("virustotal",),
    },
    "send-weekly-report": {
        "task": "send_weekly_report",
        "schedule": crontab(minute=0, hour=9, day_of_week=1),
    },
    "forward-to-elasticsearch-hourly": {
        "task": "forward_to_elasticsearch",
        "schedule": crontab(minute=15, hour="*"),
        "kwargs": {"lookback_hours": 2},
    },
}
