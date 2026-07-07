"""Pydantic schemas for alerts."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AlertBase(BaseModel):
    """Base alert fields."""

    title: str
    description: str | None = None
    severity: str = "info"
    cvss_score: Decimal | None = None
    source_name: str


class AlertNotesUpdate(BaseModel):
    """Payload for updating analyst notes on an alert."""
    notes: str | None = Field(default=None, max_length=5000)


class AlertResponse(AlertBase):
    """Alert response with all fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_alert_id: int
    affected_products: dict | None = None
    attack_vectors: dict | None = None
    mitre_techniques: dict | None = None
    iocs: dict | None = None
    published_date: datetime | None = None
    normalized_at: datetime
    categories: list["CategoryBrief"] = []
    notes: str | None = None
    is_acknowledged: bool = False
    acknowledged_at: datetime | None = None


class CategoryBrief(BaseModel):
    """Minimal category info for embedding in alert responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AlertListResponse(BaseModel):
    """Paginated list of alerts."""

    items: list[AlertResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AlertStatsResponse(BaseModel):
    """Aggregated alert statistics."""

    total_alerts: int
    by_severity: dict[str, int]
    by_source: dict[str, int]
    last_24h: int
    last_7d: int


# Resolve forward reference
AlertResponse.model_rebuild()
