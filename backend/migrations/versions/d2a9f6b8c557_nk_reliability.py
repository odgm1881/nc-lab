"""NK reliability queue and reconciliation

Revision ID: d2a9f6b8c557
Revises: c1f8e5a7b446
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2a9f6b8c557"
down_revision: str | None = "c1f8e5a7b446"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("nk_exchanges") as batch_op:
        batch_op.add_column(sa.Column("request_fingerprint", sa.String(64), nullable=True))
        batch_op.add_column(
            sa.Column(
                "retryable",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "reconciliation_status",
                sa.String(30),
                nullable=False,
                server_default="not_checked",
            )
        )
        batch_op.add_column(
            sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index("ix_nk_exchanges_request_fingerprint", ["request_fingerprint"])
        batch_op.create_index("ix_nk_exchanges_retryable", ["retryable"])
        batch_op.create_index("ix_nk_exchanges_reconciliation_status", ["reconciliation_status"])
    op.execute("UPDATE nk_exchanges SET request_fingerprint = id")
    with op.batch_alter_table("nk_exchanges") as batch_op:
        batch_op.alter_column("request_fingerprint", existing_type=sa.String(64), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("nk_exchanges") as batch_op:
        batch_op.drop_index("ix_nk_exchanges_reconciliation_status")
        batch_op.drop_index("ix_nk_exchanges_retryable")
        batch_op.drop_index("ix_nk_exchanges_request_fingerprint")
        batch_op.drop_column("last_reconciled_at")
        batch_op.drop_column("reconciliation_status")
        batch_op.drop_column("next_retry_at")
        batch_op.drop_column("retryable")
        batch_op.drop_column("request_fingerprint")
