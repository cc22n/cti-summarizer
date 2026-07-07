"""TrendPrediction model for ML-generated threat forecasts."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrendPrediction(Base):
    """Stores Prophet time series predictions for alert volume by severity."""

    __tablename__ = "trend_predictions"
    # Mirrors the unique index created by migration 002.
    # Without this, Alembic autogenerate detects drift and proposes to drop
    # the DB constraint on the next revision.
    __table_args__ = (
        UniqueConstraint(
            "run_id", "series_key", "target_date",
            name="ix_trend_predictions_run_series",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    series_key: Mapped[str] = mapped_column(String(20), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_count: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    lower_bound: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    upper_bound: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    model_type: Mapped[str] = mapped_column(String(20), nullable=False)
    training_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<TrendPrediction {self.series_key} {self.target_date}>"
