"""Raw and normalized alert models."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RawAlert(Base):
    """Raw ingested data from a CTI source, stored as-is."""

    __tablename__ = "raw_alerts"
    # DB-level guard against duplicate ingestion under concurrent Celery workers.
    # The orchestrator also deduplicates in Python, but only the DB constraint
    # is race-condition-safe.
    __table_args__ = (
        UniqueConstraint(
            "source_id", "external_id", name="uq_raw_alerts_source_external"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    source = relationship("Source", back_populates="raw_alerts")
    normalized_alert = relationship(
        "NormalizedAlert", back_populates="raw_alert", uselist=False
    )

    def __repr__(self) -> str:
        return f"<RawAlert {self.external_id}>"


class NormalizedAlert(Base):
    """Normalized, enriched alert ready for analysis and display."""

    __tablename__ = "normalized_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_alert_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("raw_alerts.id"),
        nullable=False,
        unique=True,
        # index=True omitted: unique=True already creates a unique index
        # in PostgreSQL, which is usable for equality lookups.
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info", index=True
    )  # critical/high/medium/low/info
    cvss_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 1), nullable=True
    )
    affected_products: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    attack_vectors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mitre_techniques: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    iocs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    published_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    normalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Semantic search embedding stored as JSON array of floats
    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Analyst annotations
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    raw_alert = relationship("RawAlert", back_populates="normalized_alert")
    categories = relationship(
        "AlertCategory",
        secondary="alert_category_map",
        back_populates="alerts",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<NormalizedAlert {self.title[:40]}>"
