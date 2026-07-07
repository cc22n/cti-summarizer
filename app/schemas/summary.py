"""Pydantic schemas for summary endpoints."""

import math
from datetime import datetime

from pydantic import BaseModel, Field


class SummaryResponse(BaseModel):
    """Single summary response."""

    id: int
    normalized_alert_id: int | None
    summary_type: str
    content: str
    model_used: str
    prompt_tokens: int | None
    completion_tokens: int | None
    period_start: datetime | None
    period_end: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SummaryListResponse(BaseModel):
    """Paginated list of summaries."""

    items: list[SummaryResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SummarizeRequest(BaseModel):
    """Request body for on-demand alert summarization."""

    alert_ids: list[int] = Field(min_length=1, max_length=100)


class DigestRequest(BaseModel):
    """Request body for on-demand digest generation."""

    hours: int = 24  # how many hours back to include
