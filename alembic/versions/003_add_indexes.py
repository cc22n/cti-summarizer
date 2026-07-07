"""Add performance indexes on normalized_alerts.

Revision ID: 003
Revises: 002
Create Date: 2026-04-08
"""

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # postgresql_concurrently=True requires that the migration NOT run inside
    # a transaction (Alembic wraps upgrades in BEGIN/COMMIT by default).
    # Using it inside a transaction raises:
    #   "CREATE INDEX CONCURRENTLY cannot run inside a transaction block"
    # The indexes are created normally here; if you need true CONCURRENTLY
    # on a live production database, run the CREATE INDEX statement manually
    # with `transaction_per_migration = false` in alembic.ini or use
    # op.execute() with a raw DDL statement outside a transaction block.
    op.create_index(
        "ix_normalized_alerts_severity_date",
        "normalized_alerts",
        ["severity", "normalized_at"],
    )
    op.create_index(
        "ix_normalized_alerts_published_date",
        "normalized_alerts",
        ["published_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_normalized_alerts_severity_date", table_name="normalized_alerts"
    )
    op.drop_index(
        "ix_normalized_alerts_published_date", table_name="normalized_alerts"
    )
