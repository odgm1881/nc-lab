"""add NK API exchange tracking

Revision ID: c126c2b59e10
Revises: 8c21d5e8a0f2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c126c2b59e10"
down_revision: str | None = "8c21d5e8a0f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("nk_exchanges") as batch_op:
        batch_op.add_column(sa.Column("error_code", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("external_id", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("correlation_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("duration_ms", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_nk_exchanges_external_id", ["external_id"])
        batch_op.create_index("ix_nk_exchanges_correlation_id", ["correlation_id"])


def downgrade() -> None:
    with op.batch_alter_table("nk_exchanges") as batch_op:
        batch_op.drop_index("ix_nk_exchanges_correlation_id")
        batch_op.drop_index("ix_nk_exchanges_external_id")
        batch_op.drop_column("last_attempt_at")
        batch_op.drop_column("duration_ms")
        batch_op.drop_column("correlation_id")
        batch_op.drop_column("external_id")
        batch_op.drop_column("error_code")
