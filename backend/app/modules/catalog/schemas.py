"""Pydantic-схемы каталога карточек (API-контракт)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.validation.schemas import IssueOut, ValidationResultOut


class CardCreateIn(BaseModel):
    name: str = ""
    vendor_code: str = ""
    category_code: str | None = None
    gtin: str | None = None
    attributes: dict = Field(default_factory=dict)
    rd_data: dict = Field(default_factory=dict)


class CardUpdateIn(BaseModel):
    name: str | None = None
    vendor_code: str | None = None
    category_code: str | None = None
    gtin: str | None = None
    attributes: dict | None = None
    rd_data: dict | None = None


class CardOut(BaseModel):
    id: str
    client_id: str
    name: str
    vendor_code: str
    category_code: str | None
    gtin: str | None
    status: str
    attributes: dict
    rd_data: dict
    validation_issues: list[IssueOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CardListOut(BaseModel):
    items: list[CardOut]
    total: int


class CardValidateOut(BaseModel):
    card: CardOut
    result: ValidationResultOut


# --- построение карточек из вариаций модели ---


class BuildFromVariationsIn(BaseModel):
    name: str = Field(description="Наименование модели")
    base_vendor_code: str = "SKU"
    category_code: str | None = None
    # общие атрибуты для всех SKU (состав, бренд, возрастная группа и т.п.)
    common_attributes: dict = Field(default_factory=dict)
    rd_data: dict = Field(default_factory=dict)
    colors: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    genders: list[str] = Field(default_factory=list)
    completeness: list[str] = Field(default_factory=list)


class BuildFromVariationsOut(BaseModel):
    created: int
    cards: list[CardOut]
