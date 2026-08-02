from datetime import datetime

from pydantic import BaseModel, Field


class AuditEventOut(BaseModel):
    id: str
    actor_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    before: dict | None
    after: dict | None
    details: dict = Field(default_factory=dict)
    correlation_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
