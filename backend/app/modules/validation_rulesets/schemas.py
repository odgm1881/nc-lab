from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class RuleSetCreateIn(BaseModel):
    version: str = Field(min_length=1, max_length=40, pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    title: str = Field(min_length=2, max_length=255)
    category_codes: list[str] = Field(default_factory=list, max_length=100)
    rule_names: list[str] | None = Field(default=None, min_length=1, max_length=100)
    source_reference: str = Field(min_length=3, max_length=4000)
    change_summary: str = Field(default="", max_length=4000)
    effective_from: date
    effective_to: date | None = None

    @field_validator("category_codes")
    @classmethod
    def normalize_categories(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    @field_validator("rule_names")
    @classmethod
    def normalize_rule_names(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    @model_validator(mode="after")
    def validate_period(self) -> "RuleSetCreateIn":
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Дата окончания действия не может быть раньше даты начала.")
        return self


class RuleSetApproveIn(BaseModel):
    expert_name: str | None = Field(default=None, max_length=255)


class RuleSetOut(BaseModel):
    id: str
    version: str
    title: str
    status: str
    category_codes: list[str]
    rule_names: list[str]
    source_reference: str
    change_summary: str
    effective_from: date | None
    effective_to: date | None
    created_by: str
    approved_by: str | None
    approved_by_name: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RuleSetListOut(BaseModel):
    items: list[RuleSetOut]
    total: int
