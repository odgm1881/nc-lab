"""SQLAlchemy-модель задания импорта. Статус храним полем, без очередей."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import JSONBType
from app.database import Base

# Статусы импорта: pending → processing → done | error.
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_DONE = "done"
STATUS_ERROR = "error"


def _uuid() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # excel | csv | onec
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_PENDING)
    rows_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cards_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_success: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_error: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ImportRowResult(Base):
    __tablename__ = "import_row_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    card_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    raw_data: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    mapped_data: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    errors: Mapped[list] = mapped_column(JSONBType, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MappingProfile(Base):
    __tablename__ = "mapping_profiles"
    __table_args__ = (
        UniqueConstraint("client_id", "name", name="uq_mapping_profile_client_name"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="csv")
    mapping: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
