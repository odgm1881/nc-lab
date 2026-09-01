"""Pydantic-схемы модуля оператора."""

from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreateIn(BaseModel):
    card_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default="other", max_length=40)
    note: str | None = Field(default=None, max_length=4000)
    escalation_reason: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    priority: int = Field(default=2, ge=1, le=3)


class TaskUpdateIn(BaseModel):
    status: str | None = None
    category: str | None = Field(default=None, max_length=40)
    priority: int | None = Field(default=None, ge=1, le=3)
    note: str | None = Field(default=None, max_length=4000)
    assignee_id: str | None = None
    escalation_reason: str | None = Field(default=None, max_length=2000)
    resolution: str | None = Field(default=None, max_length=4000)
    due_at: datetime | None = None


class TaskOut(BaseModel):
    id: str
    client_id: str
    card_id: str | None
    title: str
    category: str
    note: str | None
    escalation_reason: str | None
    resolution: str | None
    priority: int
    status: str
    assignee_id: str | None
    started_at: datetime | None
    due_at: datetime | None
    resolved_at: datetime | None
    returned_at: datetime | None
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListOut(BaseModel):
    items: list[TaskOut]
    total: int


class TaskBulkAssignIn(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)
    assignee_id: str


class TaskBulkAssignOut(BaseModel):
    updated: int


class TaskCommentCreateIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class TaskCommentOut(BaseModel):
    id: str
    task_id: str
    author_id: str
    author_role: str
    author_name: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
