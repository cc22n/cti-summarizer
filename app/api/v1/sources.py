"""Sources API endpoints."""

import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_api_key
from app.limiter import limiter
from app.models.ingestion_log import IngestionLog
from app.models.source import Source
from app.models.alert import RawAlert
from app.schemas.source import (
    IngestionLogListResponse,
    IngestionLogResponse,
    SourceHealthResponse,
    SourceResponse,
)
from app.workers.ingestion_tasks import ingest_source

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
def list_sources(db: Session = Depends(get_db)):
    """List all CTI sources and their status."""
    sources = db.query(Source).order_by(Source.name).all()
    return [SourceResponse.model_validate(s) for s in sources]


@router.get("/{source_id}/health", response_model=SourceHealthResponse)
def source_health(source_id: int, db: Session = Depends(get_db)):
    """Health check for a specific source."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    # Last log status
    last_log = (
        db.query(IngestionLog)
        .filter(IngestionLog.source_id == source_id)
        .order_by(IngestionLog.started_at.desc())
        .first()
    )

    # Alerts in last 24h
    alerts_24h = (
        db.query(func.count(RawAlert.id))
        .filter(
            RawAlert.source_id == source_id,
            RawAlert.ingested_at >= cutoff,
        )
        .scalar()
        or 0
    )

    # Errors in last 24h
    errors_24h = (
        db.query(func.count(IngestionLog.id))
        .filter(
            IngestionLog.source_id == source_id,
            IngestionLog.status == "error",
            IngestionLog.started_at >= cutoff,
        )
        .scalar()
        or 0
    )

    last_error_msg: str | None = None
    if last_log and last_log.status == "error":
        last_error_msg = last_log.error_message

    # Raw alerts that failed normalization (is_processed stays False when
    # normalize_raw_alert returns None, e.g. unknown source or parse error).
    unprocessed = (
        db.query(func.count(RawAlert.id))
        .filter(
            RawAlert.source_id == source_id,
            RawAlert.is_processed == False,  # noqa: E712
        )
        .scalar()
        or 0
    )

    return SourceHealthResponse(
        source_id=source.id,
        source_name=source.name,
        is_active=source.is_active,
        last_polled_at=source.last_polled_at,
        last_status=last_log.status if last_log else None,
        last_error_message=last_error_msg,
        alerts_last_24h=alerts_24h,
        error_count_last_24h=errors_24h,
        unprocessed_count=unprocessed,
    )


@router.get("/{source_id}/logs", response_model=IngestionLogListResponse)
def source_logs(
    source_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return paginated ingestion log history for a source, newest first."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    query = (
        db.query(IngestionLog)
        .filter(IngestionLog.source_id == source_id)
        .order_by(IngestionLog.started_at.desc())
    )
    total = query.count()
    pages = math.ceil(total / page_size) if total > 0 else 1
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return IngestionLogListResponse(
        items=[IngestionLogResponse.model_validate(log) for log in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.patch("/{source_id}/toggle", response_model=SourceResponse)
def toggle_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Enable or disable a CTI source.

    Toggles the is_active flag. Disabled sources are skipped by the
    Beat scheduler but can still be polled manually.
    """
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.is_active = not source.is_active
    db.commit()
    db.refresh(source)
    return SourceResponse.model_validate(source)


@router.post("/{source_id}/poll")
@limiter.limit("10/minute")
def trigger_poll(
    request: Request,
    source_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Force ingestion of a specific source."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Map source names to adapter keys
    source_key_map = {
        "NVD": "nvd",
        "CISA_KEV": "cisa_kev",
        "OTX": "otx",
        "MITRE_ATTACK": "mitre_attack",
        "RSS": "rss",
    }
    key = source_key_map.get(source.name)
    if not key:
        raise HTTPException(
            status_code=400,
            detail=f"No adapter registered for source: {source.name}",
        )

    task = ingest_source.delay(key)
    return {
        "message": f"Ingestion triggered for {source.name}",
        "task_id": task.id,
    }
