"""operator collaboration

Revision ID: a9d6c3e5f224
Revises: f8c5b2d4e113
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9d6c3e5f224"
down_revision: str | None = "f8c5b2d4e113"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("operator_tasks") as batch_op:
        batch_op.add_column(
            sa.Column("category", sa.String(length=40), nullable=False, server_default="other")
        )
        batch_op.add_column(sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_operator_tasks_category", ["category"])

    op.create_table(
        "operator_task_comments",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("client_id", sa.String(length=32), nullable=False),
        sa.Column("task_id", sa.String(length=32), nullable=False),
        sa.Column("author_id", sa.String(length=32), nullable=False),
        sa.Column("author_role", sa.String(length=20), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_operator_task_comments_client_id", "operator_task_comments", ["client_id"]
    )
    op.create_index("ix_operator_task_comments_task_id", "operator_task_comments", ["task_id"])
    op.create_index(
        "ix_operator_task_comments_author_id", "operator_task_comments", ["author_id"]
    )
    op.create_index(
        "ix_operator_task_comments_created_at", "operator_task_comments", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_operator_task_comments_created_at", table_name="operator_task_comments")
    op.drop_index("ix_operator_task_comments_author_id", table_name="operator_task_comments")
    op.drop_index("ix_operator_task_comments_task_id", table_name="operator_task_comments")
    op.drop_index("ix_operator_task_comments_client_id", table_name="operator_task_comments")
    op.drop_table("operator_task_comments")
    with op.batch_alter_table("operator_tasks") as batch_op:
        batch_op.drop_index("ix_operator_tasks_category")
        batch_op.drop_column("returned_at")
        batch_op.drop_column("category")
