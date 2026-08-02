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
    rows_success: int
    rows_error: int


class ImportJobOut(BaseModel):
    id: str
    filename: str
    source: str
    status: str
    rows_total: int
    cards_created: int
    rows_success: int
    rows_error: int
    error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportRowResultOut(BaseModel):
    id: str
    row_number: int
    status: str
    card_id: str | None
    raw_data: dict
    mapped_data: dict
    errors: list

    model_config = {"from_attributes": True}


class MappingProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source: str = Field(default="csv", pattern="^(excel|csv|onec)$")
    mapping: dict[str, str] = Field(default_factory=dict)


class MappingProfileOut(MappingProfileIn):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
