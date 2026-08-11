from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ExchangeCreateIn(BaseModel):
    card_id: str
    mode: Literal["file", "mock"] = "file"
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class ExchangeOut(BaseModel):
    id: str
    client_id: str
    card_id: str
    idempotency_key: str
    mode: str
    status: str
    request_payload: dict
    response_payload: dict
    error: str | None
    attempts: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExchangeListOut(BaseModel):
    items: list[ExchangeOut]
    total: int
