from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.modules.catalog.schemas import CardOut
from app.modules.pilot_metrics.schemas import PilotMetricsOut


class PilotBaselineMixin(BaseModel):
    baseline_time_per_card_minutes: float | None = Field(default=None, ge=0)
    baseline_first_pass_rate: float | None = Field(default=None, ge=0, le=100)
    baseline_return_rate: float | None = Field(default=None, ge=0, le=100)
    baseline_labor_minutes_per_card: float | None = Field(default=None, ge=0)
    baseline_cost_per_card: float | None = Field(default=None, ge=0)
    operator_hourly_cost: float | None = Field(default=None, ge=0)


class PilotCreateIn(PilotBaselineMixin):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    sample_target: int = Field(default=50, ge=1, le=5000)
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    responsible: str = Field(default="", max_length=255)
    participants: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_period(self) -> "PilotCreateIn":
        if (
            self.planned_start_date
            and self.planned_end_date
            and self.planned_end_date < self.planned_start_date
        ):
            raise ValueError("Дата окончания пилота не может быть раньше даты начала.")
        return self


class PilotUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    sample_target: int | None = Field(default=None, ge=1, le=5000)
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    responsible: str | None = Field(default=None, max_length=255)
    participants: list[str] | None = Field(default=None, max_length=100)
    baseline_time_per_card_minutes: float | None = Field(default=None, ge=0)
    baseline_first_pass_rate: float | None = Field(default=None, ge=0, le=100)
    baseline_return_rate: float | None = Field(default=None, ge=0, le=100)
    baseline_labor_minutes_per_card: float | None = Field(default=None, ge=0)
    baseline_cost_per_card: float | None = Field(default=None, ge=0)
    operator_hourly_cost: float | None = Field(default=None, ge=0)


class PilotCardsIn(BaseModel):
    card_ids: list[str] = Field(min_length=1, max_length=5000)


class PilotOut(BaseModel):
    id: str
    client_id: str
    name: str
    description: str | None
    status: str
    sample_target: int
    planned_start_date: date | None
    planned_end_date: date | None
    responsible: str
    participants: list[str] = Field(default_factory=list)
    baseline_time_per_card_minutes: float | None
    baseline_first_pass_rate: float | None
    baseline_return_rate: float | None
    baseline_labor_minutes_per_card: float | None
    baseline_cost_per_card: float | None
    operator_hourly_cost: float | None
    cards_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PilotListOut(BaseModel):
    items: list[PilotOut]
    total: int


class PilotEffectOut(BaseModel):
    baseline_time_per_card_minutes: float | None
    actual_time_per_card_minutes: float | None
    time_reduction_rate: float | None
    baseline_first_pass_rate: float | None
    actual_first_pass_rate: float | None
    first_pass_change_points: float | None
    baseline_return_rate: float | None
    actual_return_rate: float | None
    return_rate_change_points: float | None
    baseline_labor_minutes_per_card: float | None
    actual_labor_minutes_per_card: float | None
    labor_reduction_rate: float | None
    baseline_cost_per_card: float | None
    actual_cost_per_card: float | None
    cost_saving_rate: float | None
    measured_indicators: int
    total_indicators: int = 5


class PilotDetailOut(PilotOut):
    cards: list[CardOut] = Field(default_factory=list)
    metrics: PilotMetricsOut
    effect: PilotEffectOut
