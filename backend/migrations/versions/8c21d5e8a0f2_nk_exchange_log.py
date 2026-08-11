"""add nk exchange log

Revision ID: 8c21d5e8a0f2
Revises: 44b9875a2233
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "8c21d5e8a0f2"
down_revision: str | None = "44b9875a2233"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nk_exchanges",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("client_id", sa.String(length=32), nullable=False),
        sa.Column("card_id", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("request_payload", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("response_payload", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "idempotency_key", name="uq_nk_exchange_client_key"),
    )
    op.create_index("ix_nk_exchanges_client_id", "nk_exchanges", ["client_id"])
    op.create_index("ix_nk_exchanges_card_id", "nk_exchanges", ["card_id"])
    op.create_index("ix_nk_exchanges_status", "nk_exchanges", ["status"])


def downgrade() -> None:
    op.drop_index("ix_nk_exchanges_status", table_name="nk_exchanges")
    op.drop_index("ix_nk_exchanges_card_id", table_name="nk_exchanges")
    op.drop_index("ix_nk_exchanges_client_id", table_name="nk_exchanges")
    op.drop_table("nk_exchanges")
