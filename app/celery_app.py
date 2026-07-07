"""Celery application configuration."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "cti_summarizer",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

# Explicitly import all task modules so Celery registers them on worker start.
# autodiscover_tasks() only finds files named 'tasks.py'; our modules use
# descriptive names (ingestion_tasks, summary_tasks, prediction_tasks).
celery_app.conf.imports = (
    "app.workers.ingestion_tasks",
    "app.workers.summary_tasks",
    "app.workers.prediction_tasks",
    "app.workers.search_tasks",
)

# The weekly-report Beat entry is defined in ingestion_tasks.py (alongside
# other Beat entries) so summary_tasks must also be imported there.
# Celery discovers send_weekly_report via the imports tuple above.
