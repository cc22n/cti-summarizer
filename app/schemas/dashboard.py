"""Pydantic schemas for dashboard endpoints."""

from datetime import date

from pydantic import BaseModel


class DashboardOverview(BaseModel):
    """Aggregated data for the main dashboard."""

    total_alerts: int
    alerts_today: int
    alerts_this_week: int
    critical_count: int
    high_count: int
    sources_active: int
    sources_total: int
    last_ingestion: str | None = None


class TimelinePoint(BaseModel):
    """Single point in a timeline series."""

    date: date
    count: int
    severity_breakdown: dict[str, int] | None = None


class TimelineResponse(BaseModel):
    """Timeline of alerts over time."""

    points: list[TimelinePoint]
    period: str  # daily/weekly
