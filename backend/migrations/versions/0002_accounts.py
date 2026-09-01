"""Add login accounts.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

from app.models import Account

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Account.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Account.__table__.drop(bind=op.get_bind(), checkfirst=True)
