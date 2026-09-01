from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import JSONBType
from app.database import Base

STATUS_PREPARATION = "preparation"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
ALL_STATUSES = (STATUS_PREPARATION, STATUS_RUNNING, STATUS_COMPLETED)


def _uuid() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class Pilot(Base):
    __tablename__ = "pilots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_PREPARATION, index=True
    )
    sample_target: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    planned_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    responsible: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    participants: Mapped[list] = mapped_column(JSONBType, nullable=False, default=list)
    baseline_time_per_card_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_first_pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_return_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_labor_minutes_per_card: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_cost_per_card: Mapped[float | None] = mapped_column(Float, nullable=True)
    operator_hourly_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class PilotCard(Base):
    __tablename__ = "pilot_cards"
    __table_args__ = (
        UniqueConstraint("pilot_id", "card_id", name="uq_pilot_card"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    pilot_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    card_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
