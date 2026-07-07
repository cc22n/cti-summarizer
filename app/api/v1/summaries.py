"""Summaries API endpoints."""

import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_api_key
from app.limiter import limiter
from app.models.alert import NormalizedAlert
from app.models.summary import Summary
from app.schemas.summary import (
    DigestRequest,
    SummaryListResponse,
    SummaryResponse,
    SummarizeRequest,
)

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get("", response_model=SummaryListResponse)
def list_summaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    summary_type: str | None = Query(None),
    normalized_alert_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """List summaries with pagination and optional filters."""
    query = db.query(Summary)

    if summary_type:
        query = query.filter(Summary.summary_type == summary_type)
    if normalized_alert_id is not None:
        query = query.filter(
            Summary.normalized_alert_id == normalized_alert_id
        )

    total = query.count()
    pages = math.ceil(total / page_size) if total > 0 else 1

    items = (
        query.order_by(Summary.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return SummaryListResponse(
        items=[SummaryResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# NOTE: /digest/latest must be declared before /{summary_id}
# to avoid FastAPI treating "digest" as an integer parameter.
@router.get("/digest/latest", response_model=SummaryResponse)
def get_latest_digest(db: Session = Depends(get_db)):
    """Return the most recent digest summary."""
    summary = (
        db.query(Summary)
        .filter(Summary.summary_type == "digest")
        .order_by(Summary.created_at.desc())
        .first()
    )
    if not summary:
        raise HTTPException(status_code=404, detail="No digest summaries found")
    return SummaryResponse.model_validate(summary)


@router.get("/{summary_id}", response_model=SummaryResponse)
def get_summary(summary_id: int, db: Session = Depends(get_db)):
    """Get a single summary by ID."""
    summary = db.query(Summary).filter(Summary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return SummaryResponse.model_validate(summary)


@router.post("/generate")
@limiter.limit("30/minute")
def generate_summaries(
    request: Request,
    body: SummarizeRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Trigger on-demand summarization for specific alert IDs via Celery."""
    if not body.alert_ids:
        raise HTTPException(status_code=400, detail="alert_ids cannot be empty")

    # Validate that all alert IDs exist
    existing = (
        db.query(NormalizedAlert.id)
        .filter(NormalizedAlert.id.in_(body.alert_ids))
        .all()
    )
    existing_ids = {row[0] for row in existing}
    missing = set(body.alert_ids) - existing_ids
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Alerts not found: {sorted(missing)}",
        )

    from app.workers.summary_tasks import summarize_alerts

    task = summarize_alerts.delay(body.alert_ids)
    return {
        "message": f"Summarization triggered for {len(body.alert_ids)} alerts",
        "task_id": task.id,
    }


@router.post("/digest/generate")
@limiter.limit("30/minute")
def generate_digest(
    request: Request,
    body: DigestRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Trigger on-demand digest generation for the last N hours."""
    if body.hours < 1 or body.hours > 168:
        raise HTTPException(
            status_code=400, detail="hours must be between 1 and 168"
        )

    from app.workers.summary_tasks import generate_daily_digest

    task = generate_daily_digest.delay(body.hours)
    return {
        "message": f"Digest generation triggered for last {body.hours}h",
        "task_id": task.id,
    }
