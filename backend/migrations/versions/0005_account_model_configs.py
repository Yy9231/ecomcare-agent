"""add encrypted account model configs

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 早期版本会在应用启动时执行 create_all，可能已提前创建此表，但
    # alembic_version 仍停在 0004。迁移需接管该状态，避免重复建表失败。
    inspector = sa.inspect(op.get_bind())
    if "account_model_configs" in inspector.get_table_names():
        indexes = {
            index["name"] for index in inspector.get_indexes("account_model_configs")
        }
        if "ix_account_model_configs_account_id" not in indexes:
            op.create_index(
                "ix_account_model_configs_account_id",
                "account_model_configs",
                ["account_id"],
            )
        return

    op.create_table(
        "account_model_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model_name", sa.String(160), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("account_id", "provider"),
    )
    op.create_index("ix_account_model_configs_account_id", "account_model_configs", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_account_model_configs_account_id", table_name="account_model_configs")
    op.drop_table("account_model_configs")
