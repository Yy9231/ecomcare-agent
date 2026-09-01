"""add account model preferences

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS model_provider VARCHAR(40)")
    op.execute("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS model_name VARCHAR(160)")


def downgrade() -> None:
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS model_name")
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS model_provider")
