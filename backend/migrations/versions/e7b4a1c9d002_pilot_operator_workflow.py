"""pilot operator workflow

Revision ID: e7b4a1c9d002
Revises: c126c2b59e10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7b4a1c9d002"
down_revision: str | None = "c126c2b59e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("operator_tasks") as batch_op:
        batch_op.add_column(sa.Column("escalation_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("resolution", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_operator_tasks_due_at", ["due_at"])


def downgrade() -> None:
    with op.batch_alter_table("operator_tasks") as batch_op:
        batch_op.drop_index("ix_operator_tasks_due_at")
        batch_op.drop_column("resolved_at")
        batch_op.drop_column("due_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("resolution")
        batch_op.drop_column("escalation_reason")
