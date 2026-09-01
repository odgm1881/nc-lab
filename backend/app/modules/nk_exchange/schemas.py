from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ExchangeCreateIn(BaseModel):
    card_id: str
    mode: Literal["file", "mock", "api"] = "file"
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class ExchangeOut(BaseModel):
    id: str
    client_id: str
    card_id: str
    idempotency_key: str
    request_fingerprint: str
    mode: str
    status: str
    request_payload: dict
    response_payload: dict
    error: str | None
    error_code: str | None
    external_id: str | None
    correlation_id: str | None
    attempts: int
    retryable: bool
    next_retry_at: datetime | None
    duration_ms: int | None
    last_attempt_at: datetime | None
    reconciliation_status: str
    last_reconciled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExchangeListOut(BaseModel):
    items: list[ExchangeOut]
    total: int


class IntegrationStatusOut(BaseModel):
    api_enabled: bool
    base_url: str
    auth_method: Literal["api_key", "bearer", "none"]
    attribute_mappings: int
    category_mappings: int
    file_mode_available: bool = True
    mock_mode_available: bool = True


class ExchangeBulkOut(BaseModel):
    processed: int
    succeeded: int
    failed: int
    items: list[ExchangeOut] = Field(default_factory=list)


class ExchangeQueueSummaryOut(BaseModel):
    total: int
    failed: int
    retry_due: int
    processing: int
    stale_payload: int
