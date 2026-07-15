"""Pydantic-схемы модуля валидации (API-контракт)."""

from pydantic import BaseModel, Field


class IssueOut(BaseModel):
    code: str
    severity: str
    message: str
    field: str | None = None


class ValidationResultOut(BaseModel):
    is_valid: bool
    errors: list[IssueOut] = Field(default_factory=list)
    warnings: list[IssueOut] = Field(default_factory=list)
    issues: list[IssueOut] = Field(default_factory=list)


class CardValidationIn(BaseModel):
    """Карточка для разовой проверки без сохранения."""

    category_code: str | None = None
    gtin: str | None = None
    attributes: dict = Field(default_factory=dict)
    rd_data: dict = Field(default_factory=dict)


class RulesOut(BaseModel):
    rules: list[str]
