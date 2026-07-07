"""Alerts API endpoints."""

import csv
import io
import json
import math
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app import cache
from app.database import get_async_db, get_db
from app.dependencies import require_api_key
from app.limiter import limiter
from app.models.alert import NormalizedAlert
from app.models.category import AlertCategory, alert_category_map
from app.schemas.alert import (
    AlertListResponse,
    AlertNotesUpdate,
    AlertResponse,
    AlertStatsResponse,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])

_STATS_KEY = "alerts:stats"
_STATS_TTL = 60


def _apply_search(query, search: str, db=None):
    """Apply text search filter to a NormalizedAlert query.

    Uses PostgreSQL tsvector + GIN index (ix_normalized_alerts_fulltext)
    when the active session is connected to PostgreSQL; falls back to
    ILIKE for SQLite (used in tests).
    """
    use_tsvector = False
    try:
        if db is not None:
            bind = db.get_bind()
            use_tsvector = bind.dialect.name == "postgresql"
        else:
            from app.database import get_engine
            use_tsvector = get_engine().dialect.name == "postgresql"
    except Exception:
        pass

    if use_tsvector:
        query = query.filter(
            func.to_tsvector(
                "english",
                func.coalesce(NormalizedAlert.title, "")
                + " "
                + func.coalesce(NormalizedAlert.description, ""),
            ).op("@@")(func.plainto_tsquery("english", search[:200]))
        )
    else:
        search_clean = search[:100].replace("%", r"\%").replace("_", r"\_")
        query = query.filter(
            NormalizedAlert.title.ilike(f"%{search_clean}%", escape="\\")
            | NormalizedAlert.description.ilike(f"%{search_clean}%", escape="\\")
        )
    return query


# Severity is stored as text; sort by threat rank, not alphabetically.
# desc -> critical first, asc -> info first. Unknown values sort last.
_SEVERITY_RANK = case(
    (NormalizedAlert.severity == "critical", 5),
    (NormalizedAlert.severity == "high", 4),
    (NormalizedAlert.severity == "medium", 3),
    (NormalizedAlert.severity == "low", 2),
    (NormalizedAlert.severity == "info", 1),
    else_=0,
)

_SORT_FIELDS: dict = {
    "normalized_at": NormalizedAlert.normalized_at,
    "published_date": NormalizedAlert.published_date,
    "severity": _SEVERITY_RANK,
    "cvss_score": NormalizedAlert.cvss_score,
    "source_name": NormalizedAlert.source_name,
    "title": NormalizedAlert.title,
}


def _apply_sort(query, sort_by: str, sort_order: str):
    col = _SORT_FIELDS.get(sort_by, NormalizedAlert.normalized_at)
    return query.order_by(col.asc() if sort_order == "asc" else col.desc())


@router.get("", response_model=AlertListResponse)
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: str | None = Query(None),
    source: str | None = Query(None),
    search: str | None = Query(None),
    category: str | None = Query(None, description="Filter by category name"),
    date_from: datetime | None = Query(
        None,
        description="ISO 8601 lower bound on COALESCE(published_date, normalized_at)",
    ),
    date_to: datetime | None = Query(
        None,
        description="ISO 8601 upper bound on COALESCE(published_date, normalized_at)",
    ),
    sort_by: str = Query(
        "normalized_at",
        description="Sort field: normalized_at | published_date | severity | cvss_score | source_name | title",
    ),
    sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    is_acknowledged: bool | None = Query(
        None, description="Filter by acknowledgment status"
    ),
    db: Session = Depends(get_db),
):
    """List normalized alerts with pagination, filtering, and sorting."""
    query = db.query(NormalizedAlert)

    if severity:
        query = query.filter(NormalizedAlert.severity == severity)
    if source:
        query = query.filter(NormalizedAlert.source_name == source)
    if search:
        query = _apply_search(query, search, db)
    if category:
        query = (
            query.join(
                alert_category_map,
                NormalizedAlert.id == alert_category_map.c.alert_id,
            )
            .join(
                AlertCategory,
                AlertCategory.id == alert_category_map.c.category_id,
            )
            .filter(AlertCategory.name == category)
        )
    if date_from or date_to:
        date_field = func.coalesce(
            NormalizedAlert.published_date, NormalizedAlert.normalized_at
        )
        if date_from:
            query = query.filter(date_field >= date_from)
        if date_to:
            query = query.filter(date_field <= date_to)
    if is_acknowledged is not None:
        query = query.filter(NormalizedAlert.is_acknowledged == is_acknowledged)

    # Single round-trip: window function returns total alongside each row.
    # Falls back to a separate count() only when the requested page is empty
    # (past the last page), which is the uncommon case.
    rows = (
        _apply_sort(
            query.add_columns(func.count().over().label("_total")),
            sort_by,
            sort_order,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    if rows:
        total = rows[0][1]
        items = [row[0] for row in rows]
    else:
        total = query.count()
        items = []

    pages = math.ceil(total / page_size) if total > 0 else 1

    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/stats", response_model=AlertStatsResponse)
def alert_stats(db: Session = Depends(get_db)):
    """Aggregated alert statistics (cached 60s)."""
    cached = cache.get_cached(_STATS_KEY)
    if cached is not None:
        return AlertStatsResponse(**cached)

    total = db.query(func.count(NormalizedAlert.id)).scalar() or 0

    severity_rows = (
        db.query(NormalizedAlert.severity, func.count(NormalizedAlert.id))
        .group_by(NormalizedAlert.severity)
        .all()
    )
    by_severity = {row[0]: row[1] for row in severity_rows}

    source_rows = (
        db.query(NormalizedAlert.source_name, func.count(NormalizedAlert.id))
        .group_by(NormalizedAlert.source_name)
        .all()
    )
    by_source = {row[0]: row[1] for row in source_rows}

    now = datetime.now(timezone.utc)
    last_24h = (
        db.query(func.count(NormalizedAlert.id))
        .filter(NormalizedAlert.normalized_at >= now - timedelta(hours=24))
        .scalar()
        or 0
    )
    last_7d = (
        db.query(func.count(NormalizedAlert.id))
        .filter(NormalizedAlert.normalized_at >= now - timedelta(days=7))
        .scalar()
        or 0
    )

    result = AlertStatsResponse(
        total_alerts=total,
        by_severity=by_severity,
        by_source=by_source,
        last_24h=last_24h,
        last_7d=last_7d,
    )

    cache.set_cached(_STATS_KEY, result.model_dump(), ttl=_STATS_TTL)
    return result


@router.get("/export")
@limiter.limit("10/minute")
def export_alerts(
    request: Request,
    severity: str | None = Query(None),
    source: str | None = Query(None),
    search: str | None = Query(None),
    category: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    format: str = Query("csv", description="Export format: csv or stix"),
    db: Session = Depends(get_db),
):
    """Export normalized alerts as CSV or STIX 2.1 bundle (max 10,000 rows)."""
    query = db.query(NormalizedAlert)

    if severity:
        query = query.filter(NormalizedAlert.severity == severity)
    if source:
        query = query.filter(NormalizedAlert.source_name == source)
    if search:
        query = _apply_search(query, search, db)
    if category:
        query = (
            query.join(
                alert_category_map,
                NormalizedAlert.id == alert_category_map.c.alert_id,
            )
            .join(
                AlertCategory,
                AlertCategory.id == alert_category_map.c.category_id,
            )
            .filter(AlertCategory.name == category)
        )
    if date_from or date_to:
        date_field = func.coalesce(
            NormalizedAlert.published_date, NormalizedAlert.normalized_at
        )
        if date_from:
            query = query.filter(date_field >= date_from)
        if date_to:
            query = query.filter(date_field <= date_to)

    limit = 2_000 if format == "stix" else 10_000
    alerts = (
        query.order_by(NormalizedAlert.normalized_at.desc())
        .limit(limit)
        .all()
    )

    if format == "stix":
        return _export_stix(alerts)
    return _export_csv(alerts)


def _csv_safe(value: str | None) -> str:
    """Neutralize spreadsheet formula injection in feed-controlled text.

    Titles come from external CTI feeds; a leading =, +, -, @, tab or CR
    makes Excel/LibreOffice evaluate the cell as a formula on open.
    """
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value or ""


def _export_csv(alerts: list) -> StreamingResponse:
    """Stream alerts as CSV."""
    def _rows():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "title", "severity", "source_name", "cvss_score",
            "published_date", "normalized_at",
        ])
        yield buf.getvalue()

        for alert in alerts:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                alert.id,
                _csv_safe(alert.title),
                alert.severity,
                alert.source_name,
                float(alert.cvss_score) if alert.cvss_score else "",
                alert.published_date.isoformat() if alert.published_date else "",
                alert.normalized_at.isoformat() if alert.normalized_at else "",
            ])
            yield buf.getvalue()

    return StreamingResponse(
        _rows(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alerts.csv"},
    )


def _export_stix(alerts: list) -> StreamingResponse:
    """Stream a STIX 2.1 bundle one object at a time to avoid building the
    full JSON string in memory."""
    _CONFIDENCE = {"critical": 90, "high": 70, "medium": 50, "low": 30, "info": 10}

    def _stream():
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        bundle_id = f"bundle--{uuid.uuid4()}"
        yield f'{{"type":"bundle","id":"{bundle_id}","objects":['
        first = True
        for alert in alerts:
            published = (
                alert.published_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                if alert.published_date
                else now_iso
            )
            modified = (
                alert.normalized_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                if alert.normalized_at
                else now_iso
            )
            obj = {
                "type": "indicator",
                "spec_version": "2.1",
                "id": f"indicator--{uuid.uuid5(uuid.NAMESPACE_DNS, f'cti-{alert.id}')}",
                "created": published,
                "modified": modified,
                "name": alert.title[:256],
                "description": (alert.description or "")[:2000],
                "confidence": _CONFIDENCE.get(alert.severity, 10),
                "labels": [alert.severity, alert.source_name.lower()],
                "pattern": (
                    f"[domain-name:value = "
                    f"'{alert.source_name.lower()}-alert-{alert.id}']"
                ),
                "pattern_type": "stix",
                "valid_from": published,
                "extensions": {
                    "x-cti-alert": {
                        "source_name": alert.source_name,
                        "severity": alert.severity,
                        "cvss_score": (
                            str(alert.cvss_score) if alert.cvss_score else None
                        ),
                        "iocs": alert.iocs,
                        "mitre_techniques": alert.mitre_techniques,
                    }
                },
            }
            if not first:
                yield ","
            yield json.dumps(obj, default=str)
            first = False
        yield "]}"

    return StreamingResponse(
        _stream(),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=alerts.stix2.json"},
    )


@router.get("/semantic-search", summary="Semantic similarity search over alerts")
async def semantic_search(
    q: str = Query(..., min_length=1, max_length=200, description="Natural language query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
):
    """Search alerts by semantic similarity using xAI text embeddings.

    Uses a true async SQLAlchemy session (psycopg v3 native async) so the
    event loop is not blocked during DB access.  Falls back to ILIKE search
    when the embedding API is unavailable.
    """
    from app.services.embedding_service import semantic_rank

    search_clean = q[:100].replace("%", r"\%").replace("_", r"\_")

    result = await db.execute(
        select(NormalizedAlert)
        .where(
            NormalizedAlert.title.ilike(f"%{search_clean}%", escape="\\")
            | NormalizedAlert.description.ilike(f"%{search_clean}%", escape="\\")
        )
        .order_by(NormalizedAlert.normalized_at.desc())
        .limit(100)
    )
    candidates = list(result.scalars().all())

    if not candidates:
        result = await db.execute(
            select(NormalizedAlert)
            .order_by(NormalizedAlert.normalized_at.desc())
            .limit(200)
        )
        candidates = list(result.scalars().all())

    if not candidates:
        return {"query": q, "results": [], "method": "text", "total": 0}

    texts = [f"{a.title} {(a.description or '')[:300]}" for a in candidates]
    scores = await semantic_rank(q, texts)

    if scores is not None:
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        results = [a for a, _ in ranked[:limit]]
        method = "semantic"
    else:
        results = candidates[:limit]
        method = "text"

    return {
        "query": q,
        "results": [AlertResponse.model_validate(a) for a in results],
        "method": method,
        "total": len(results),
    }


@router.get("/correlations")
@limiter.limit("5/minute")
def alert_correlations(
    request: Request,
    min_count: int = Query(2, ge=2, description="Minimum alerts to form a group"),
    db: Session = Depends(get_db),
):
    """Group alerts by shared CVE ID in title or shared vendor in affected_products.

    Returns correlation groups with at least min_count members.
    Rate-limited to 5 requests/minute (grouping is CPU-intensive in Python).
    """
    alerts = (
        db.query(NormalizedAlert)
        .order_by(NormalizedAlert.normalized_at.desc())
        .limit(1000)
        .all()
    )

    # Group by CVE ID extracted from title (e.g. "CVE-2024-12345")
    cve_groups: dict[str, list] = {}
    vendor_groups: dict[str, list] = {}

    cve_pattern = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)

    for alert in alerts:
        # CVE grouping
        cve_matches = cve_pattern.findall(alert.title or "")
        for cve_id in cve_matches:
            key = cve_id.upper()
            cve_groups.setdefault(key, []).append(alert)

        # Vendor grouping from affected_products
        products = alert.affected_products
        if isinstance(products, dict):
            vendor = products.get("vendor") or ""
            if vendor and len(vendor) > 1:
                vendor_groups.setdefault(vendor.lower(), []).append(alert)

    result = []

    for cve_id, group_alerts in cve_groups.items():
        if len(group_alerts) < min_count:
            continue
        result.append({
            "group_type": "cve",
            "key": cve_id,
            "count": len(group_alerts),
            "severities": list({a.severity for a in group_alerts}),
            "sources": list({a.source_name for a in group_alerts}),
            "alert_ids": [a.id for a in group_alerts[:20]],
        })

    for vendor, group_alerts in vendor_groups.items():
        if len(group_alerts) < min_count:
            continue
        result.append({
            "group_type": "vendor",
            "key": vendor,
            "count": len(group_alerts),
            "severities": list({a.severity for a in group_alerts}),
            "sources": list({a.source_name for a in group_alerts}),
            "alert_ids": [a.id for a in group_alerts[:20]],
        })

    # Sort by count desc
    result.sort(key=lambda x: x["count"], reverse=True)
    return {"groups": result[:100]}


@router.patch("/{alert_id}/notes", response_model=AlertResponse, summary="Update analyst notes")
def update_notes(
    alert_id: int,
    body: AlertNotesUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """Set or clear analyst investigation notes for an alert."""
    alert = db.query(NormalizedAlert).filter(NormalizedAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.notes = body.notes
    db.commit()
    db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse, summary="Toggle acknowledgment")
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """Toggle the acknowledged flag on an alert.

    Acknowledged alerts have been reviewed by an analyst.
    Calling this endpoint again un-acknowledges the alert.
    """
    alert = db.query(NormalizedAlert).filter(NormalizedAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_acknowledged = not alert.is_acknowledged
    alert.acknowledged_at = (
        datetime.now(timezone.utc) if alert.is_acknowledged else None
    )
    db.commit()
    db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get a single alert by ID."""
    alert = db.query(NormalizedAlert).filter(
        NormalizedAlert.id == alert_id
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)
