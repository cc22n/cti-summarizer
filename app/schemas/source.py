"""Pydantic schemas for sources."""

import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceResponse(BaseModel):
    """Source status response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    base_url: str
    polling_interval_minutes: int
    is_active: bool
    last_polled_at: datetime | None = None
    created_at: datetime


class SourceHealthResponse(BaseModel):
    """Health check for a specific source."""

    source_id: int
    source_name: str
    is_active: bool
    last_polled_at: datetime | None = None
    last_status: str | None = None
    last_error_message: str | None = None
    alerts_last_24h: int = 0
    error_count_last_24h: int = 0
    unprocessed_count: int = 0


class IngestionLogResponse(BaseModel):
    """Single ingestion log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    alerts_fetched: int
    alerts_new: int
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class IngestionLogListResponse(BaseModel):
    """Paginated ingestion log history."""

    items: list[IngestionLogResponse]
    total: int
    page: int
    page_size: int
    pages: int
