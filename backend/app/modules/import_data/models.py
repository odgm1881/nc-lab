"""SQLAlchemy-модель задания импорта. Статус храним полем, без очередей."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

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
    storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
