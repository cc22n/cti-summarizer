"""Predictions API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_api_key
from app.limiter import limiter
from app.models.trend_prediction import TrendPrediction
from app.schemas.prediction import (
    PredictionGenerateResponse,
    PredictionLatestResponse,
    PredictionPoint,
    TaskStatusResponse,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/latest", response_model=PredictionLatestResponse)
def get_latest_predictions(db: Session = Depends(get_db)):
    """Return the most recent prediction run for all series (14 target dates)."""
    # Group only by run_id so a run with mixed model types (prophet + rolling_avg)
    # doesn't produce duplicate rows. min(model_type) prefers "prophet" over
    # "rolling_avg" alphabetically, which is the more informative label.
    latest = (
        db.query(
            TrendPrediction.run_id,
            func.max(TrendPrediction.generated_at).label("generated_at"),
            func.max(TrendPrediction.training_days).label("training_days"),
            func.min(TrendPrediction.model_type).label("model_type"),
        )
        .group_by(TrendPrediction.run_id)
        .order_by(func.max(TrendPrediction.generated_at).desc())
        .first()
    )

    if not latest:
        raise HTTPException(status_code=404, detail="No predictions available yet")

    rows = (
        db.query(TrendPrediction)
        .filter(TrendPrediction.run_id == latest.run_id)
        .order_by(TrendPrediction.series_key, TrendPrediction.target_date)
        .all()
    )

    series: dict[str, list[PredictionPoint]] = {}
    for row in rows:
        if row.series_key not in series:
            series[row.series_key] = []
        series[row.series_key].append(
            PredictionPoint(
                date=row.target_date,
                predicted=row.predicted_count,
                lower=row.lower_bound,
                upper=row.upper_bound,
                is_anomaly=row.is_anomaly,
            )
        )

    return PredictionLatestResponse(
        run_id=latest.run_id,
        generated_at=latest.generated_at,
        training_days=latest.training_days,
        model_type=latest.model_type,
        series=series,
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    """Get Celery task status by ID."""
    from app.celery_app import celery_app

    try:
        result = celery_app.AsyncResult(task_id)
        status = result.status
        task_result = result.result if result.ready() else None
        if isinstance(task_result, Exception):
            task_result = {"error": str(task_result)}
        elif task_result is not None and not isinstance(task_result, dict):
            task_result = {"value": str(task_result)}
    except Exception:
        return TaskStatusResponse(task_id=task_id, status="UNKNOWN", result=None)

    return TaskStatusResponse(task_id=task_id, status=status, result=task_result)


@router.post("/generate", response_model=PredictionGenerateResponse)
@limiter.limit("10/minute")
def trigger_prediction(request: Request, _: str = Depends(require_api_key)):
    """Trigger an on-demand prediction run via Celery task."""
    from app.workers.prediction_tasks import run_prediction_task

    task = run_prediction_task.delay()
    return PredictionGenerateResponse(task_id=task.id, status="queued")
