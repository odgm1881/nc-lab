"""Pydantic-схемы модуля оператора."""

from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreateIn(BaseModel):
    card_id: str | None = None
    title: str
    note: str | None = None
    priority: int = Field(default=2, ge=1, le=3)


class TaskUpdateIn(BaseModel):
    status: str | None = None
    priority: int | None = Field(default=None, ge=1, le=3)
    note: str | None = None
    assignee_id: str | None = None


class TaskOut(BaseModel):
    id: str
    client_id: str
    card_id: str | None
    title: str
    note: str | None
    priority: int
    status: str
    assignee_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListOut(BaseModel):
    items: list[TaskOut]
    total: int
