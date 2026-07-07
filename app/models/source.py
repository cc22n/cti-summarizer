"""CTI source model (NVD, CISA KEV, OTX, MITRE, RSS)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(Base):
    """Represents a CTI data feed source."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # api, rss, stix
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    polling_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=360
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    raw_alerts = relationship("RawAlert", back_populates="source", lazy="select")
    ingestion_logs = relationship(
        "IngestionLog", back_populates="source", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Source {self.name} ({self.source_type})>"
