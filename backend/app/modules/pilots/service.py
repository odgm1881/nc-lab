from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.modules.audit import service as audit_service
from app.modules.catalog.models import Card
from app.modules.catalog.schemas import CardOut
from app.modules.pilot_metrics import service as metrics_service
from app.modules.pilots.models import (
    STATUS_COMPLETED,
    STATUS_PREPARATION,
    STATUS_RUNNING,
    Pilot,
    PilotCard,
)
from app.modules.pilots.schemas import (
    PilotCreateIn,
    PilotDetailOut,
    PilotEffectOut,
    PilotListOut,
    PilotOut,
    PilotUpdateIn,
)


def _require(db: Session, client_id: str, pilot_id: str) -> Pilot:
    pilot = db.scalar(
        select(Pilot).where(Pilot.id == pilot_id, Pilot.client_id == client_id)
    )
    if pilot is None:
        raise NotFoundError("Пилот не найден.")
    return pilot


def _card_ids(db: Session, pilot_id: str) -> list[str]:
    return list(
        db.scalars(
            select(PilotCard.card_id)
            .where(PilotCard.pilot_id == pilot_id)
            .order_by(PilotCard.added_at.asc())
        )
    )


def _normalize_people(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        clean = value.strip()
        if clean and clean not in result:
            result.append(clean)
    return result


def _validate_period(start: date | None, end: date | None) -> None:
    if start and end and end < start:
        raise DomainError("Дата окончания пилота не может быть раньше даты начала.")


def _required_text(value: str | None, label: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise DomainError(f"Поле «{label}» не может быть пустым.")
    return clean


def _to_out(pilot: Pilot, cards_count: int) -> PilotOut:
    return PilotOut(
        id=pilot.id,
        client_id=pilot.client_id,
        name=pilot.name,
        description=pilot.description,
        status=pilot.status,
        sample_target=pilot.sample_target,
        planned_start_date=pilot.planned_start_date,
        planned_end_date=pilot.planned_end_date,
        responsible=pilot.responsible,
        participants=list(pilot.participants or []),
        baseline_time_per_card_minutes=pilot.baseline_time_per_card_minutes,
        baseline_first_pass_rate=pilot.baseline_first_pass_rate,
        baseline_return_rate=pilot.baseline_return_rate,
        baseline_labor_minutes_per_card=pilot.baseline_labor_minutes_per_card,
        baseline_cost_per_card=pilot.baseline_cost_per_card,
        operator_hourly_cost=pilot.operator_hourly_cost,
        cards_count=cards_count,
        started_at=pilot.started_at,
        completed_at=pilot.completed_at,
        created_at=pilot.created_at,
        updated_at=pilot.updated_at,
    )


def _reduction(baseline: float | None, actual: float | None) -> float | None:
    if baseline is None or actual is None or baseline <= 0:
        return None
    return round((baseline - actual) / baseline * 100, 1)


def _change(actual: float | None, baseline: float | None) -> float | None:
    if baseline is None or actual is None:
        return None
    return round(actual - baseline, 1)


def _effect(pilot: Pilot, metrics) -> PilotEffectOut:
    baseline_cost = pilot.baseline_cost_per_card
    if (
        baseline_cost is None
        and pilot.baseline_labor_minutes_per_card is not None
        and pilot.operator_hourly_cost is not None
    ):
        baseline_cost = round(
            pilot.baseline_labor_minutes_per_card * pilot.operator_hourly_cost / 60, 2
        )
    actual_cost = None
    if (
        metrics.median_operator_resolution_minutes is not None
        and pilot.operator_hourly_cost is not None
    ):
        actual_cost = round(
            metrics.median_operator_resolution_minutes * pilot.operator_hourly_cost / 60, 2
        )
    comparisons = (
        (pilot.baseline_time_per_card_minutes, metrics.median_time_to_ready_minutes),
        (pilot.baseline_first_pass_rate, metrics.first_pass_validation_rate),
        (pilot.baseline_return_rate, metrics.operator_return_rate),
        (
            pilot.baseline_labor_minutes_per_card,
            metrics.median_operator_resolution_minutes,
        ),
        (baseline_cost, actual_cost),
    )
    return PilotEffectOut(
        baseline_time_per_card_minutes=pilot.baseline_time_per_card_minutes,
        actual_time_per_card_minutes=metrics.median_time_to_ready_minutes,
        time_reduction_rate=_reduction(
            pilot.baseline_time_per_card_minutes, metrics.median_time_to_ready_minutes
        ),
        baseline_first_pass_rate=pilot.baseline_first_pass_rate,
        actual_first_pass_rate=metrics.first_pass_validation_rate,
        first_pass_change_points=_change(
            metrics.first_pass_validation_rate, pilot.baseline_first_pass_rate
        ),
        baseline_return_rate=pilot.baseline_return_rate,
        actual_return_rate=metrics.operator_return_rate,
        return_rate_change_points=_change(
            metrics.operator_return_rate, pilot.baseline_return_rate
        ),
        baseline_labor_minutes_per_card=pilot.baseline_labor_minutes_per_card,
        actual_labor_minutes_per_card=metrics.median_operator_resolution_minutes,
        labor_reduction_rate=_reduction(
            pilot.baseline_labor_minutes_per_card,
            metrics.median_operator_resolution_minutes,
        ),
        baseline_cost_per_card=baseline_cost,
        actual_cost_per_card=actual_cost,
        cost_saving_rate=_reduction(baseline_cost, actual_cost),
        measured_indicators=sum(
            baseline is not None and actual is not None
            for baseline, actual in comparisons
        ),
    )


def _detail(db: Session, pilot: Pilot) -> PilotDetailOut:
    ids = _card_ids(db, pilot.id)
    cards = list(
        db.scalars(
            select(Card).where(Card.client_id == pilot.client_id, Card.id.in_(ids))
        )
    )
    by_id = {card.id: card for card in cards}
    ordered = [by_id[card_id] for card_id in ids if card_id in by_id]
    metrics = metrics_service.calculate(
        db,
        pilot.client_id,
        card_ids=set(ids),
        sample_target=pilot.sample_target,
    )
    base = _to_out(pilot, len(ordered))
    return PilotDetailOut(
        **base.model_dump(),
        cards=[CardOut.model_validate(card) for card in ordered],
        metrics=metrics,
        effect=_effect(pilot, metrics),
    )


def list_pilots(db: Session, client_id: str) -> PilotListOut:
    pilots = list(
        db.scalars(
            select(Pilot)
            .where(Pilot.client_id == client_id)
            .order_by(Pilot.created_at.desc())
        )
    )
    counts = dict(
        db.execute(
            select(PilotCard.pilot_id, func.count(PilotCard.id))
            .where(PilotCard.client_id == client_id)
            .group_by(PilotCard.pilot_id)
        ).all()
    )
    return PilotListOut(
        items=[_to_out(pilot, int(counts.get(pilot.id, 0))) for pilot in pilots],
        total=len(pilots),
    )


def create_pilot(
    db: Session,
    client_id: str,
    data: PilotCreateIn,
    actor_id: str | None = None,
) -> PilotDetailOut:
    pilot = Pilot(
        client_id=client_id,
        name=_required_text(data.name, "Название"),
        description=data.description,
        sample_target=data.sample_target,
        planned_start_date=data.planned_start_date,
        planned_end_date=data.planned_end_date,
        responsible=data.responsible.strip(),
        participants=_normalize_people(data.participants),
        baseline_time_per_card_minutes=data.baseline_time_per_card_minutes,
        baseline_first_pass_rate=data.baseline_first_pass_rate,
        baseline_return_rate=data.baseline_return_rate,
        baseline_labor_minutes_per_card=data.baseline_labor_minutes_per_card,
        baseline_cost_per_card=data.baseline_cost_per_card,
        operator_hourly_cost=data.operator_hourly_cost,
        status=STATUS_PREPARATION,
    )
    db.add(pilot)
    db.flush()
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="pilot.created",
        entity_type="pilot",
        entity_id=pilot.id,
        after=audit_service.snapshot(pilot),
    )
    db.commit()
    db.refresh(pilot)
    return _detail(db, pilot)


def get_pilot(db: Session, client_id: str, pilot_id: str) -> PilotDetailOut:
    return _detail(db, _require(db, client_id, pilot_id))


def update_pilot(
    db: Session,
    client_id: str,
    pilot_id: str,
    data: PilotUpdateIn,
    actor_id: str | None = None,
) -> PilotDetailOut:
    pilot = _require(db, client_id, pilot_id)
    before = audit_service.snapshot(pilot)
    fields = data.model_fields_set
    start = data.planned_start_date if "planned_start_date" in fields else pilot.planned_start_date
    end = data.planned_end_date if "planned_end_date" in fields else pilot.planned_end_date
    _validate_period(start, end)
    if "name" in fields:
        pilot.name = _required_text(data.name, "Название")
    if "sample_target" in fields:
        if data.sample_target is None:
            raise DomainError("Целевой размер выборки не может быть пустым.")
        pilot.sample_target = data.sample_target
    if "responsible" in fields:
        pilot.responsible = (data.responsible or "").strip()
    for field in (
        "description",
        "planned_start_date",
        "planned_end_date",
        "baseline_time_per_card_minutes",
        "baseline_first_pass_rate",
        "baseline_return_rate",
        "baseline_labor_minutes_per_card",
        "baseline_cost_per_card",
        "operator_hourly_cost",
    ):
        if field in fields:
            setattr(pilot, field, getattr(data, field))
    if "participants" in fields:
        pilot.participants = _normalize_people(data.participants)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="pilot.updated",
        entity_type="pilot",
        entity_id=pilot.id,
        before=before,
        after=audit_service.snapshot(pilot),
    )
    db.commit()
    db.refresh(pilot)
    return _detail(db, pilot)


def add_cards(
    db: Session,
    client_id: str,
    pilot_id: str,
    card_ids: list[str],
    actor_id: str | None = None,
) -> PilotDetailOut:
    pilot = _require(db, client_id, pilot_id)
    if pilot.status != STATUS_PREPARATION:
        raise ConflictError("Состав выборки уже зафиксирован и не может быть изменён.")
    requested = list(dict.fromkeys(card_ids))
    owned = set(
        db.scalars(
            select(Card.id).where(Card.client_id == client_id, Card.id.in_(requested))
        )
    )
    missing = [card_id for card_id in requested if card_id not in owned]
    if missing:
        raise NotFoundError("Одна или несколько карточек не найдены.")
    existing = set(_card_ids(db, pilot.id))
    added = [card_id for card_id in requested if card_id not in existing]
    db.add_all(
        [
            PilotCard(client_id=client_id, pilot_id=pilot.id, card_id=card_id)
            for card_id in added
        ]
    )
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="pilot.cards_added",
        entity_type="pilot",
        entity_id=pilot.id,
        details={"card_ids": added, "count": len(added)},
    )
    db.commit()
    return _detail(db, pilot)


def remove_card(
    db: Session,
    client_id: str,
    pilot_id: str,
    card_id: str,
    actor_id: str | None = None,
) -> PilotDetailOut:
    pilot = _require(db, client_id, pilot_id)
    if pilot.status != STATUS_PREPARATION:
        raise ConflictError("Состав выборки уже зафиксирован и не может быть изменён.")
    link = db.scalar(
        select(PilotCard).where(
            PilotCard.pilot_id == pilot.id,
            PilotCard.client_id == client_id,
            PilotCard.card_id == card_id,
        )
    )
    if link is None:
        raise NotFoundError("Карточка не входит в выборку пилота.")
    db.delete(link)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="pilot.card_removed",
        entity_type="pilot",
        entity_id=pilot.id,
        details={"card_id": card_id},
    )
    db.commit()
    return _detail(db, pilot)


def start_pilot(
    db: Session, client_id: str, pilot_id: str, actor_id: str | None = None
) -> PilotDetailOut:
    pilot = _require(db, client_id, pilot_id)
    if pilot.status != STATUS_PREPARATION:
        raise ConflictError("Запустить можно только пилот в состоянии подготовки.")
    if not _card_ids(db, pilot.id):
        raise DomainError("Добавьте хотя бы одну карточку в выборку пилота.")
    before = audit_service.snapshot(pilot)
    pilot.status = STATUS_RUNNING
    pilot.started_at = datetime.now(UTC)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="pilot.started",
        entity_type="pilot",
        entity_id=pilot.id,
        before=before,
        after=audit_service.snapshot(pilot),
        details={"cards_count": len(_card_ids(db, pilot.id))},
    )
    db.commit()
    db.refresh(pilot)
    return _detail(db, pilot)


def complete_pilot(
    db: Session, client_id: str, pilot_id: str, actor_id: str | None = None
) -> PilotDetailOut:
    pilot = _require(db, client_id, pilot_id)
    if pilot.status != STATUS_RUNNING:
        raise ConflictError("Завершить можно только запущенный пилот.")
    before = audit_service.snapshot(pilot)
    pilot.status = STATUS_COMPLETED
    pilot.completed_at = datetime.now(UTC)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="pilot.completed",
        entity_type="pilot",
        entity_id=pilot.id,
        before=before,
        after=audit_service.snapshot(pilot),
    )
    db.commit()
    db.refresh(pilot)
    return _detail(db, pilot)


def export_report(db: Session, client_id: str, pilot_id: str) -> bytes:
    detail = get_pilot(db, client_id, pilot_id)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["pilot", detail.name])
    writer.writerow(["status", detail.status])
    writer.writerow(["period_start", detail.planned_start_date or ""])
    writer.writerow(["period_end", detail.planned_end_date or ""])
    writer.writerow(["responsible", detail.responsible])
    writer.writerow(["participants", ", ".join(detail.participants)])
    writer.writerow([])
    writer.writerow(["effect_metric", "baseline", "actual", "change"])
    effect = detail.effect
    for key, baseline, actual, change in (
        (
            "time_per_card_minutes",
            effect.baseline_time_per_card_minutes,
            effect.actual_time_per_card_minutes,
            effect.time_reduction_rate,
        ),
        (
            "first_pass_rate",
            effect.baseline_first_pass_rate,
            effect.actual_first_pass_rate,
            effect.first_pass_change_points,
        ),
        (
            "return_rate",
            effect.baseline_return_rate,
            effect.actual_return_rate,
            effect.return_rate_change_points,
        ),
        (
            "labor_minutes_per_card",
            effect.baseline_labor_minutes_per_card,
            effect.actual_labor_minutes_per_card,
            effect.labor_reduction_rate,
        ),
        (
            "cost_per_card",
            effect.baseline_cost_per_card,
            effect.actual_cost_per_card,
            effect.cost_saving_rate,
        ),
    ):
        writer.writerow(
            [
                key,
                baseline if baseline is not None else "",
                actual if actual is not None else "",
                change if change is not None else "",
            ]
        )
    writer.writerow([])
    writer.writerow(["metric", "value"])
    for key, value in detail.metrics.model_dump(
        mode="json", exclude={"top_issue_codes", "notes"}
    ).items():
        writer.writerow([key, "" if value is None else value])
    for issue in detail.metrics.top_issue_codes:
        writer.writerow([f"issue.{issue.code}", issue.count])
    for index, note in enumerate(detail.metrics.notes, start=1):
        writer.writerow([f"note.{index}", note])
    writer.writerow([])
    writer.writerow(["card_id", "name", "vendor_code", "gtin", "status"])
    for card in detail.cards:
        writer.writerow([card.id, card.name, card.vendor_code, card.gtin or "", card.status])
    return ("\ufeff" + output.getvalue()).encode("utf-8")
