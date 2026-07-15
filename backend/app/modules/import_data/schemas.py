"""Pydantic-схемы модуля импорта."""

from datetime import datetime

from pydantic import BaseModel, Field


class NomenclatureRowOut(BaseModel):
    name: str
    vendor_code: str
    category_code: str | None = None
    gtin: str | None = None
    attributes: dict = Field(default_factory=dict)
    rd_data: dict = Field(default_factory=dict)


class ImportPreviewOut(BaseModel):
    source: str
    rows_total: int
    rows: list[NomenclatureRowOut]


class ImportCommitOut(BaseModel):
    job_id: str
    source: str
    rows_total: int
    cards_created: int


class ImportJobOut(BaseModel):
    id: str
    filename: str
    source: str
    status: str
    rows_total: int
    cards_created: int
    error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
