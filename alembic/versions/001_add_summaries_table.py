"""Add summaries table.

Revision ID: 001
Revises: (none - first migration)
Create Date: 2026-04-01
"""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "summaries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "normalized_alert_id",
            sa.Integer,
            sa.ForeignKey("normalized_alerts.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("summary_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=True),
        sa.Column("completion_tokens", sa.Integer, nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_summaries_summary_type", "summaries", ["summary_type"])
    op.create_index("ix_summaries_created_at", "summaries", ["created_at"])
    # Partial unique index: only one "alert"-type summary per normalized alert
    op.create_index(
        "uq_summaries_alert_type",
        "summaries",
        ["normalized_alert_id"],
        unique=True,
        postgresql_where=sa.text(
            "normalized_alert_id IS NOT NULL AND summary_type = 'alert'"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_summaries_alert_type", table_name="summaries")
    op.drop_index("ix_summaries_created_at", table_name="summaries")
    op.drop_index("ix_summaries_summary_type", table_name="summaries")
    op.drop_table("summaries")
