"""pilot baseline and measured effect

Revision ID: b0e7d4f6a335
Revises: a9d6c3e5f224
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b0e7d4f6a335"
down_revision: str | None = "a9d6c3e5f224"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("pilots") as batch_op:
        batch_op.add_column(sa.Column("baseline_time_per_card_minutes", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("baseline_first_pass_rate", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("baseline_return_rate", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("baseline_labor_minutes_per_card", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("baseline_cost_per_card", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("operator_hourly_cost", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("pilots") as batch_op:
        batch_op.drop_column("operator_hourly_cost")
        batch_op.drop_column("baseline_cost_per_card")
        batch_op.drop_column("baseline_labor_minutes_per_card")
        batch_op.drop_column("baseline_return_rate")
        batch_op.drop_column("baseline_first_pass_rate")
        batch_op.drop_column("baseline_time_per_card_minutes")
