"""Add agent conversation read state.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS agent_last_read_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS agent_last_read_at")
