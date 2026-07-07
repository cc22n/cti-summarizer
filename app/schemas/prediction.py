"""Pydantic schemas for prediction endpoints."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class PredictionPoint(BaseModel):
    """Single forecast point for one target date."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    predicted: Decimal
    lower: Decimal
    upper: Decimal
    is_anomaly: bool = False

    @field_serializer("predicted", "lower", "upper")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v)


class PredictionLatestResponse(BaseModel):
    """Response from GET /predictions/latest."""

    run_id: str
    generated_at: datetime
    training_days: int
    model_type: str
    series: dict[str, list[PredictionPoint]]


class PredictionGenerateResponse(BaseModel):
    """Response from POST /predictions/generate."""

    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """Response from GET /predictions/tasks/{task_id}."""

    task_id: str
    status: str
    result: dict | None = None
