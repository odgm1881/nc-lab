"""validation rule sets

Revision ID: c1f8e5a7b446
Revises: b0e7d4f6a335
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.types import JSONBType

revision: str = "c1f8e5a7b446"
down_revision: str | None = "b0e7d4f6a335"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "validation_rule_sets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("category_codes", JSONBType, nullable=False),
        sa.Column("rule_names", JSONBType, nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(length=32), nullable=False),
        sa.Column("approved_by", sa.String(length=32), nullable=True),
        sa.Column("approved_by_name", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_validation_rule_sets_version",
        "validation_rule_sets",
        ["version"],
        unique=True,
    )
    op.create_index("ix_validation_rule_sets_status", "validation_rule_sets", ["status"])
    op.create_index(
        "ix_validation_rule_sets_effective_from",
        "validation_rule_sets",
        ["effective_from"],
    )
    op.create_index("ix_validation_rule_sets_created_by", "validation_rule_sets", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_validation_rule_sets_created_by", table_name="validation_rule_sets")
    op.drop_index("ix_validation_rule_sets_effective_from", table_name="validation_rule_sets")
    op.drop_index("ix_validation_rule_sets_status", table_name="validation_rule_sets")
    op.drop_index("ix_validation_rule_sets_version", table_name="validation_rule_sets")
    op.drop_table("validation_rule_sets")
