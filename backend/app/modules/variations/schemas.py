"""Pydantic-схемы модуля вариаций (API-контракт)."""

from pydantic import BaseModel, Field


class VariationAxesIn(BaseModel):
    base_vendor_code: str = Field(default="SKU", description="Базовый артикул модели")
    colors: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    genders: list[str] = Field(default_factory=list)
    completeness: list[str] = Field(default_factory=list)


class VariationOut(BaseModel):
    sku: str
    color: str | None = None
    size: str | None = None
    gender: str | None = None
    completeness: str | None = None


class VariationPreviewOut(BaseModel):
    count: int
    variations: list[VariationOut]
