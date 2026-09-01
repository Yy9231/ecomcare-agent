"""Initial EcomCare schema.

Revision ID: 0001
Revises: None
"""

from alembic import op

from app import models  # noqa: F401
from app.database import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
