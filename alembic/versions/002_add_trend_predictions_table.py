"""Add trend_predictions table.

Revision ID: 002
Revises: 001
Create Date: 2026-04-01
"""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trend_predictions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("series_key", sa.String(20), nullable=False),
        sa.Column("target_date", sa.Date, nullable=False),
        sa.Column("predicted_count", sa.Numeric(10, 2), nullable=False),
        sa.Column("lower_bound", sa.Numeric(10, 2), nullable=False),
        sa.Column("upper_bound", sa.Numeric(10, 2), nullable=False),
        sa.Column("model_type", sa.String(20), nullable=False),
        sa.Column("training_days", sa.Integer, nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_trend_predictions_run_id", "trend_predictions", ["run_id"])
    op.create_index("ix_trend_predictions_generated_at", "trend_predictions", ["generated_at"])
    op.create_index(
        "ix_trend_predictions_run_series",
        "trend_predictions",
        ["run_id", "series_key", "target_date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_trend_predictions_run_series", table_name="trend_predictions")
    op.drop_index("ix_trend_predictions_generated_at", table_name="trend_predictions")
    op.drop_index("ix_trend_predictions_run_id", table_name="trend_predictions")
    op.drop_table("trend_predictions")
