"""Alert category model and mapping table."""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Many-to-many association table.
# The composite PK (alert_id, category_id) only supports lookups by alert_id
# (leftmost prefix). Queries that filter by category_id alone (e.g. "all alerts
# in category X") need a dedicated index on category_id.
alert_category_map = Table(
    "alert_category_map",
    Base.metadata,
    Column(
        "alert_id",
        Integer,
        ForeignKey("normalized_alerts.id"),
        primary_key=True,
    ),
    Column(
        "category_id",
        Integer,
        ForeignKey("alert_categories.id"),
        primary_key=True,
    ),
    Index("ix_alert_category_map_category_id", "category_id"),
)


class AlertCategory(Base):
    """Threat category (ransomware, phishing, etc.)."""

    __tablename__ = "alert_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    alerts = relationship(
        "NormalizedAlert",
        secondary=alert_category_map,
        back_populates="categories",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<AlertCategory {self.name}>"
