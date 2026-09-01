from datetime import datetime

from pydantic import BaseModel, Field


class IssueFrequencyOut(BaseModel):
    code: str
    count: int


class PilotMetricsOut(BaseModel):
    generated_at: datetime
    cards_total: int
    cards_ready: int
    readiness_rate: float
    imported_rows_total: int
    imported_rows_without_errors: int
    import_success_rate: float | None
    imported_cards_first_pass_valid: int
    imported_cards_total: int
    first_pass_validation_rate: float | None
    median_time_to_ready_minutes: float | None
    operator_tasks_total: int
    operator_tasks_resolved: int
    operator_tasks_returned: int
    operator_return_rate: float | None
    operator_resolution_rate: float | None
    median_operator_resolution_minutes: float | None
    overdue_operator_tasks: int
    top_issue_codes: list[IssueFrequencyOut] = Field(default_factory=list)
    pilot_sample_target: int = 50
    pilot_sample_reached: bool
    notes: list[str] = Field(default_factory=list)
