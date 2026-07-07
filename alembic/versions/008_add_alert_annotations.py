"""Add analyst annotation fields to normalized_alerts.

Adds:
  - notes         TEXT NULL      — analyst investigation notes
  - is_acknowledged BOOLEAN NOT NULL DEFAULT false — reviewed flag
  - acknowledged_at TIMESTAMPTZ NULL — when it was acknowledged

Revision ID: 008
Revises: 007
Create Date: 2026-06-22
"""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("normalized_alerts", sa.Column("notes", sa.Text, nullable=True))
    op.add_column(
        "normalized_alerts",
        sa.Column(
            "is_acknowledged",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "normalized_alerts",
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_normalized_alerts_acknowledged",
        "normalized_alerts",
        ["is_acknowledged"],
    )


def downgrade() -> None:
    op.drop_index("ix_normalized_alerts_acknowledged", table_name="normalized_alerts")
    op.drop_column("normalized_alerts", "acknowledged_at")
    op.drop_column("normalized_alerts", "is_acknowledged")
    op.drop_column("normalized_alerts", "notes")
