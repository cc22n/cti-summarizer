"""Dashboard API endpoints."""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app import cache
from app.database import get_db
from app.models.alert import NormalizedAlert
from app.models.source import Source
from app.schemas.dashboard import (
    DashboardOverview,
    TimelinePoint,
    TimelineResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_OVERVIEW_KEY = "dashboard:overview"
_OVERVIEW_TTL = 60  # seconds


@router.get("/overview", response_model=DashboardOverview)
def dashboard_overview(db: Session = Depends(get_db)):
    """Aggregated data for the main dashboard (cached 60s)."""
    cached = cache.get_cached(_OVERVIEW_KEY)
    if cached is not None:
        return DashboardOverview(**cached)

    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    # Single query for all alert counts.
    # func.count(case(...)) counts the number of non-NULL values returned by
    # the CASE expression, which equals the number of rows where the condition
    # is true -- this is valid ANSI SQL and works in both SQLite and PostgreSQL.
    stats = db.query(
        func.count(NormalizedAlert.id).label("total"),
        func.sum(
            case((NormalizedAlert.normalized_at >= cutoff_24h, 1), else_=0)
        ).label("today"),
        func.sum(
            case((NormalizedAlert.normalized_at >= cutoff_7d, 1), else_=0)
        ).label("week"),
        func.sum(
            case((NormalizedAlert.severity == "critical", 1), else_=0)
        ).label("critical"),
        func.sum(
            case((NormalizedAlert.severity == "high", 1), else_=0)
        ).label("high"),
    ).one()

    total = stats.total or 0
    today = stats.today or 0
    week = stats.week or 0
    critical = stats.critical or 0
    high = stats.high or 0

    # Single query for source counts
    source_stats = db.query(
        func.count(Source.id).label("total"),
        func.sum(case((Source.is_active == True, 1), else_=0)).label("active"),
    ).one()

    sources_total = source_stats.total or 0
    sources_active = source_stats.active or 0

    # Last ingestion timestamp
    last = db.query(func.max(Source.last_polled_at)).scalar()
    last_str = last.isoformat() if last else None

    result = DashboardOverview(
        total_alerts=total,
        alerts_today=today,
        alerts_this_week=week,
        critical_count=critical,
        high_count=high,
        sources_active=sources_active,
        sources_total=sources_total,
        last_ingestion=last_str,
    )

    cache.set_cached(_OVERVIEW_KEY, result.model_dump(), ttl=_OVERVIEW_TTL)
    return result


@router.get("/timeline", response_model=TimelineResponse)
def dashboard_timeline(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """Timeline of alerts per day over the given period."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    rows = (
        db.query(
            func.date(NormalizedAlert.normalized_at).label("day"),
            NormalizedAlert.severity,
            func.count(NormalizedAlert.id).label("cnt"),
        )
        .filter(NormalizedAlert.normalized_at >= start)
        .group_by("day", NormalizedAlert.severity)
        .order_by("day")
        .all()
    )

    # Aggregate by day
    day_map: dict = {}
    for day_str, severity, cnt in rows:
        # func.date() returns string in SQLite, date in PostgreSQL
        day = date.fromisoformat(day_str) if isinstance(day_str, str) else day_str
        if day not in day_map:
            day_map[day] = {"count": 0, "severity_breakdown": {}}
        day_map[day]["count"] += cnt
        day_map[day]["severity_breakdown"][severity] = cnt

    points = [
        TimelinePoint(
            date=day,
            count=data["count"],
            severity_breakdown=data["severity_breakdown"],
        )
        for day, data in sorted(day_map.items())
    ]

    return TimelineResponse(points=points, period="daily")
