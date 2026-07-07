"""Add is_anomaly column to trend_predictions.

Revision ID: 004
Revises: 003
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trend_predictions",
        sa.Column(
            "is_anomaly",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("trend_predictions", "is_anomaly")
