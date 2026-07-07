"""LLM-generated summary model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Summary(Base):
    """Stores LLM-generated summaries for individual alerts or digests."""

    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    normalized_alert_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("normalized_alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # "alert" = per-alert summary, "digest" = batch/daily digest
    summary_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # For digest: the time window covered
    period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationship
    normalized_alert = relationship("NormalizedAlert", lazy="select")

    def __repr__(self) -> str:
        return f"<Summary id={self.id} type={self.summary_type}>"
