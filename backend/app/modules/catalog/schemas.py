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
    packaging: dict = Field(default_factory=dict)
    data_source: str = Field(default="manual", max_length=40)
    service_comment: str | None = Field(default=None, max_length=4000)


class CardUpdateIn(BaseModel):
    name: str | None = None
    vendor_code: str | None = None
    category_code: str | None = None
    gtin: str | None = None
    attributes: dict | None = None
    rd_data: dict | None = None
    packaging: dict | None = None
    data_source: str | None = Field(default=None, max_length=40)
    service_comment: str | None = Field(default=None, max_length=4000)


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
    packaging: dict
    data_source: str
    service_comment: str | None
    ruleset_version: str | None
    reference_data_version: str | None
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
    colors: list[str] = Field(default_factory=list, max_length=100)
    sizes: list[str] = Field(default_factory=list, max_length=100)
    genders: list[str] = Field(default_factory=list, max_length=100)
    completeness: list[str] = Field(default_factory=list, max_length=100)


class BuildFromVariationsOut(BaseModel):
    created: int
    cards: list[CardOut]


# --- массовая валидация ---


class ValidateAllOut(BaseModel):
    validated: int  # сколько карточек прогнали
    valid: int  # сколько теперь валидных (всего у клиента)
    error: int  # сколько теперь с ошибками (всего у клиента)


class CardBulkUpdateIn(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)
    category_code: str | None = None
    data_source: str | None = Field(default=None, max_length=40)
    service_comment: str | None = Field(default=None, max_length=4000)
    attributes: dict | None = None
    packaging: dict | None = None


class CardBulkUpdateOut(BaseModel):
    updated: int


class CardExportIn(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=5000)
    status: str | None = None
    category_code: str | None = None
    name: str | None = None
    search: str | None = None


# --- группировка по модели ---


class ModelGroupOut(BaseModel):
    name: str  # наименование модели (товара)
    category_code: str | None = None
    total: int
    counts: dict[str, int] = Field(default_factory=dict)  # статус -> количество


class ModelsOut(BaseModel):
    items: list[ModelGroupOut]
