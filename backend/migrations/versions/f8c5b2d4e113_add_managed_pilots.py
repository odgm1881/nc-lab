"""add managed pilots

Revision ID: f8c5b2d4e113
Revises: e7b4a1c9d002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.types import JSONBType

revision: str = "f8c5b2d4e113"
down_revision: str | None = "e7b4a1c9d002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pilots",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("client_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sample_target", sa.Integer(), nullable=False),
        sa.Column("planned_start_date", sa.Date(), nullable=True),
        sa.Column("planned_end_date", sa.Date(), nullable=True),
        sa.Column("responsible", sa.String(length=255), nullable=False),
        sa.Column("participants", JSONBType, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pilots_client_id", "pilots", ["client_id"])
    op.create_index("ix_pilots_status", "pilots", ["status"])
    op.create_table(
        "pilot_cards",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("client_id", sa.String(length=32), nullable=False),
        sa.Column("pilot_id", sa.String(length=32), nullable=False),
        sa.Column("card_id", sa.String(length=32), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id", "card_id", name="uq_pilot_card"),
    )
    op.create_index("ix_pilot_cards_client_id", "pilot_cards", ["client_id"])
    op.create_index("ix_pilot_cards_pilot_id", "pilot_cards", ["pilot_id"])
    op.create_index("ix_pilot_cards_card_id", "pilot_cards", ["card_id"])


def downgrade() -> None:
    op.drop_index("ix_pilot_cards_card_id", table_name="pilot_cards")
    op.drop_index("ix_pilot_cards_pilot_id", table_name="pilot_cards")
    op.drop_index("ix_pilot_cards_client_id", table_name="pilot_cards")
    op.drop_table("pilot_cards")
    op.drop_index("ix_pilots_status", table_name="pilots")
    op.drop_index("ix_pilots_client_id", table_name="pilots")
    op.drop_table("pilots")
