from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import UTC, datetime
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import STATUS_PUBLISHED, Card
from app.modules.import_data.models import ImportJob, ImportRowResult
from app.modules.operator.models import STATUS_RESOLVED, STATUS_WAITING_CLIENT, OperatorTask
from app.modules.pilot_metrics.schemas import IssueFrequencyOut, PilotMetricsOut


def _rate(part: int, total: int) -> float | None:
    return round(part / total * 100, 1) if total else None


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _median_minutes(values: list[float]) -> float | None:
    return round(median(values) / 60, 1) if values else None


def calculate(
    db: Session,
    client_id: str,
    *,
    card_ids: set[str] | None = None,
    sample_target: int = 50,
) -> PilotMetricsOut:
    now = datetime.now(UTC)
    card_stmt = select(Card).where(Card.client_id == client_id)
    import_stmt = select(ImportRowResult).where(
        ImportRowResult.client_id == client_id,
        ImportRowResult.card_id.is_not(None),
    )
    task_stmt = select(OperatorTask).where(OperatorTask.client_id == client_id)
    if card_ids is not None:
        card_stmt = card_stmt.where(Card.id.in_(card_ids))
        import_stmt = import_stmt.where(ImportRowResult.card_id.in_(card_ids))
        task_stmt = task_stmt.where(OperatorTask.card_id.in_(card_ids))

    cards = list(db.scalars(card_stmt))
    import_rows = list(db.scalars(import_stmt))
    tasks = list(db.scalars(task_stmt))
    jobs = (
        list(db.scalars(select(ImportJob).where(ImportJob.client_id == client_id)))
        if card_ids is None
        else []
    )

    ready = sum(card.status == STATUS_PUBLISHED for card in cards)
    imported_total = (
        sum(job.rows_total for job in jobs) if card_ids is None else len(import_rows)
    )
    imported_without_errors = (
        sum(job.rows_success for job in jobs)
        if card_ids is None
        else sum(row.status == "imported" for row in import_rows)
    )
    first_pass_valid = sum(row.status == "imported" for row in import_rows)

    issue_counts: Counter[str] = Counter()
    for card in cards:
        for issue in card.validation_issues or []:
            code = str(issue.get("code") or "UNKNOWN")
            issue_counts[code] += 1

    event_stmt = select(AuditEvent).where(
        AuditEvent.client_id == client_id,
        AuditEvent.entity_type == "card",
        AuditEvent.action.in_(("card.created", "card.marked_ready")),
    )
    if card_ids is not None:
        event_stmt = event_stmt.where(AuditEvent.entity_id.in_(card_ids))
    events = list(db.scalars(event_stmt.order_by(AuditEvent.created_at.asc())))
    created_at: dict[str, datetime] = {}
    ready_seconds: list[float] = []
    for event in events:
        if not event.entity_id:
            continue
        if event.action == "card.created":
            created_at.setdefault(event.entity_id, _utc(event.created_at))
        elif event.action == "card.marked_ready" and event.entity_id in created_at:
            ready_seconds.append(
                max(0.0, (_utc(event.created_at) - created_at.pop(event.entity_id)).total_seconds())
            )

    resolved = [task for task in tasks if task.status == STATUS_RESOLVED]
    returned = [
        task
        for task in tasks
        if task.returned_at is not None or task.status == STATUS_WAITING_CLIENT
    ]
    resolution_seconds = [
        max(0.0, (_utc(task.resolved_at) - _utc(task.started_at)).total_seconds())
        for task in resolved
        if task.started_at and task.resolved_at
    ]
    overdue = sum(
        bool(task.due_at and task.status != STATUS_RESOLVED and _utc(task.due_at) < now)
        for task in tasks
    )

    notes: list[str] = []
    if len(cards) < sample_target:
        notes.append(
            f"Осталось добавить до целевой выборки: {sample_target - len(cards)}."
        )
    if not jobs and card_ids is None:
        notes.append("Нет завершённых импортов: показатель успешного импорта ещё не измерен.")
    if ready and not ready_seconds:
        notes.append("Для части готовых карточек отсутствует полная временная история.")

    return PilotMetricsOut(
        generated_at=now,
        cards_total=len(cards),
        cards_ready=ready,
        readiness_rate=_rate(ready, len(cards)) or 0.0,
        imported_rows_total=imported_total,
        imported_rows_without_errors=imported_without_errors,
        import_success_rate=_rate(imported_without_errors, imported_total),
        imported_cards_first_pass_valid=first_pass_valid,
        imported_cards_total=len(import_rows),
        first_pass_validation_rate=_rate(first_pass_valid, len(import_rows)),
        median_time_to_ready_minutes=_median_minutes(ready_seconds),
        operator_tasks_total=len(tasks),
        operator_tasks_resolved=len(resolved),
        operator_tasks_returned=len(returned),
        operator_return_rate=_rate(len(returned), len(tasks)),
        operator_resolution_rate=_rate(len(resolved), len(tasks)),
        median_operator_resolution_minutes=_median_minutes(resolution_seconds),
        overdue_operator_tasks=overdue,
        top_issue_codes=[
            IssueFrequencyOut(code=code, count=count)
            for code, count in issue_counts.most_common(8)
        ],
        pilot_sample_target=sample_target,
        pilot_sample_reached=len(cards) >= sample_target,
        notes=notes,
    )


def export_csv(metrics: PilotMetricsOut) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["metric", "value"])
    for key, value in metrics.model_dump(mode="json", exclude={"top_issue_codes", "notes"}).items():
        writer.writerow([key, "" if value is None else value])
    for issue in metrics.top_issue_codes:
        writer.writerow([f"issue.{issue.code}", issue.count])
    for index, note in enumerate(metrics.notes, start=1):
        writer.writerow([f"note.{index}", note])
    return ("\ufeff" + output.getvalue()).encode("utf-8")
