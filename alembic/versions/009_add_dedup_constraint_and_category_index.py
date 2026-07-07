"""Add dedup constraint on raw_alerts and category_id index on alert_category_map.

Changes:
  - raw_alerts: unique constraint (source_id, external_id) so duplicate
    ingestion is rejected at the DB level even under concurrent Celery workers.
  - alert_category_map: index on category_id to support efficient filtering
    of alerts by category (the current composite PK only covers alert_id scans).
  - normalized_alerts: drop the redundant non-unique index ix_normalized_alerts_raw_alert_id
    (the unique=True on raw_alert_id already creates a unique index that covers
    equality lookups; having two indexes on the same column wastes space).

Revision ID: 009
Revises: 008
Create Date: 2026-06-30
"""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. DB-level deduplication guard on raw_alerts
    op.create_unique_constraint(
        "uq_raw_alerts_source_external",
        "raw_alerts",
        ["source_id", "external_id"],
    )

    # 2. Index to support "filter alerts by category" queries
    op.create_index(
        "ix_alert_category_map_category_id",
        "alert_category_map",
        ["category_id"],
    )

    # 3. Drop redundant non-unique index on normalized_alerts.raw_alert_id.
    #    The unique constraint on that column (uq or pk) already serves as an
    #    index. This index only exists on databases that went through create_all()
    #    while index=True was still set on the column, so we guard with IF EXISTS.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP INDEX IF EXISTS ix_normalized_alerts_raw_alert_id"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_normalized_alerts_raw_alert_id "
            "ON normalized_alerts (raw_alert_id)"
        )
    op.drop_index("ix_alert_category_map_category_id", table_name="alert_category_map")
    op.drop_constraint(
        "uq_raw_alerts_source_external",
        "raw_alerts",
        type_="unique",
    )
