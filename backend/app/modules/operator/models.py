"""SQLAlchemy-модель задачи оператора. Очередь = таблица со статусом и приоритетом.

Никакой сложной инфраструктуры очередей на этапе 1 (см. ARCHITECTURE.md).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Статусы задачи: open → in_progress → resolved.
STATUS_OPEN = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_RESOLVED = "resolved"

# Приоритет: 1 (низкий) .. 3 (высокий).
PRIORITY_LOW = 1
PRIORITY_NORMAL = 2
PRIORITY_HIGH = 3


def _uuid() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class OperatorTask(Base):
    __tablename__ = "operator_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    card_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=PRIORITY_NORMAL)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_OPEN, index=True)
    assignee_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
