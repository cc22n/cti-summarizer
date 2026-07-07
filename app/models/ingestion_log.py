"""Ingestion log model for tracking feed polling."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngestionLog(Base):
    """Tracks each ingestion run per source."""

    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # success/error/partial
    alerts_fetched: Mapped[int] = mapped_column(Integer, default=0)
    alerts_new: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    source = relationship("Source", back_populates="ingestion_logs")

    def __repr__(self) -> str:
        return f"<IngestionLog source={self.source_id} status={self.status}>"
