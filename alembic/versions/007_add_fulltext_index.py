"""Add GIN index for full-text search on normalized_alerts.

Only applies to PostgreSQL. SQLite used in tests ignores this migration
(the upgrade() is a no-op when the dialect is not postgresql).

Revision ID: 007
Revises: 006
Create Date: 2026-06-22
"""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_normalized_alerts_fulltext
        ON normalized_alerts
        USING GIN (
            to_tsvector(
                'english',
                coalesce(title, '') || ' ' || coalesce(description, '')
            )
        )
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        "DROP INDEX IF EXISTS ix_normalized_alerts_fulltext"
    )
