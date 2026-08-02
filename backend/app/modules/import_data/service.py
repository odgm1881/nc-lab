"""Импорт с построчным протоколом и сохраняемыми профилями колонок."""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.core.storage import new_key, storage
from app.modules.audit import service as audit_service
from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import CardCreateIn
from app.modules.import_data.models import (
    STATUS_DONE,
    STATUS_ERROR,
    ImportJob,
    ImportRowResult,
    MappingProfile,
)
from app.modules.import_data.parsers.base import (
    SOURCE_ROW_NUMBER,
    NomenclatureRow,
    map_row,
    map_rows,
)
from app.modules.import_data.parsers.csv_parser import parse_csv
from app.modules.import_data.parsers.excel import parse_excel
from app.modules.import_data.parsers.onec import parse_onec
from app.modules.import_data.schemas import (
    ImportCommitOut,
    ImportPreviewOut,
    MappingProfileIn,
    NomenclatureRowOut,
)

CANONICAL_FIELDS = {
    "name", "vendor_code", "category_code", "gtin", "item_type", "color", "size",
    "gender", "completeness", "composition", "brand", "age_group", "country",
    "rd_type", "rd_number", "rd_date", "rd_valid_until",
}

logger = logging.getLogger(__name__)


def detect_source(filename: str, source: str | None) -> str:
    if source:
        return source
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xlsm")):
        return "excel"
    if lower.endswith(".csv"):
        return "csv"
    raise DomainError("Не удалось определить формат файла. Укажите source явно.")


def _parse(source: str, content: bytes) -> list[dict]:
    parser = None
    if source == "excel":
        parser = parse_excel
    elif source == "csv":
        parser = parse_csv
    elif source == "onec":
        parser = parse_onec
    else:
        raise DomainError(f"Неизвестный источник импорта: {source}")
    try:
        return parser(content)
    except Exception as exc:
        logger.warning("import_parse_failed source=%s", source, exc_info=True)
        raise DomainError(
            "Не удалось прочитать файл. Проверьте формат и целостность данных.",
            code="IMPORT_PARSE_ERROR",
        ) from exc


def _row_to_schema(row: NomenclatureRow) -> NomenclatureRowOut:
    return NomenclatureRowOut(
        name=row.name,
        vendor_code=row.vendor_code,
        category_code=row.category_code,
        gtin=row.gtin,
        attributes=row.attributes,
        rd_data=row.rd_data,
    )


def _row_payload(row: NomenclatureRow, source: str) -> CardCreateIn:
    return CardCreateIn(
        name=row.name,
        vendor_code=row.vendor_code,
        category_code=row.category_code,
        gtin=row.gtin,
        attributes=row.attributes,
        rd_data=row.rd_data,
        data_source=source,
    )


def _json_safe(data: dict) -> dict:
    result: dict = {}
    for key, value in data.items():
        if isinstance(value, (date, datetime)):
            result[str(key)] = value.isoformat()
        elif value is None or isinstance(value, (str, int, float, bool)):
            result[str(key)] = value
        else:
            result[str(key)] = str(value)
    return result


def _csv_safe(value: object) -> object:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _validate_mapping(mapping: dict[str, str]) -> None:
    invalid = sorted(set(mapping.values()) - CANONICAL_FIELDS)
    if invalid:
        raise DomainError(f"Неизвестные целевые поля профиля: {', '.join(invalid)}")


def preview(
    filename: str,
    source: str | None,
    content: bytes,
    mapping: dict[str, str] | None = None,
) -> ImportPreviewOut:
    detected = detect_source(filename, source)
    _validate_mapping(mapping or {})
    rows = map_rows(_parse(detected, content), mapping)
    return ImportPreviewOut(
        source=detected,
        rows_total=len(rows),
        rows=[_row_to_schema(row) for row in rows],
    )


def commit(
    db: Session,
    client_id: str,
    filename: str,
    source: str | None,
    content: bytes,
    create_cards: bool = True,
    mapping: dict[str, str] | None = None,
    actor_id: str | None = None,
) -> ImportCommitOut:
    """Сохранить файл и все строки, не откатывая корректные из-за одной плохой."""
    detected = detect_source(filename, source)
    _validate_mapping(mapping or {})
    key = new_key(f"imports/{client_id}", filename)
    storage.put(key, content)
    job = ImportJob(
        client_id=client_id,
        filename=filename,
        source=detected,
        storage_key=key,
    )
    db.add(job)
    db.flush()

    try:
        raw_rows = _parse(detected, content)
        job.rows_total = len(raw_rows)
        valid: list[tuple[int, dict, CardCreateIn]] = []
        failed: list[ImportRowResult] = []
        for fallback_row_number, raw in enumerate(raw_rows, start=2):
            row_number = int(raw.get(SOURCE_ROW_NUMBER, fallback_row_number))
            safe_raw = _json_safe(
                {key: value for key, value in raw.items() if key != SOURCE_ROW_NUMBER}
            )
            try:
                mapped = map_row(raw, mapping)
                payload = _row_payload(mapped, detected)
                if not (payload.name or payload.vendor_code or payload.gtin or payload.attributes):
                    raise ValueError("Строка не содержит распознанных данных")
                valid.append((row_number, safe_raw, payload))
            except Exception as exc:  # noqa: BLE001 — ошибка должна попасть в отчёт строки
                failed.append(
                    ImportRowResult(
                        job_id=job.id,
                        client_id=client_id,
                        row_number=row_number,
                        status="error",
                        raw_data=safe_raw,
                        mapped_data={},
                        errors=[{"code": "ROW_PARSE_ERROR", "message": str(exc)}],
                    )
                )

        cards = []
        if create_cards and valid:
            cards = catalog_service.create_cards_bulk_items(
                db, client_id, [item[2] for item in valid], actor_id
            )
        for index, (row_number, raw, payload) in enumerate(valid):
            card = cards[index] if create_cards else None
            issues = list(card.validation_issues) if card is not None else []
            has_errors = any(issue.get("severity") == "error" for issue in issues)
            db.add(
                ImportRowResult(
                    job_id=job.id,
                    client_id=client_id,
                    row_number=row_number,
                    status="imported_with_errors" if has_errors else "imported",
                    card_id=card.id if card is not None else None,
                    raw_data=raw,
                    mapped_data=payload.model_dump(mode="json"),
                    errors=issues,
                )
            )
        db.add_all(failed)
        job.cards_created = len(cards)
        job.rows_success = (
            sum(
                1
                for card in cards
                if not any(i.get("severity") == "error" for i in card.validation_issues)
            )
            if create_cards
            else len(valid)
        )
        job.rows_error = len(failed) + (len(cards) - job.rows_success)
        job.status = STATUS_DONE
        audit_service.record(
            db,
            client_id=client_id,
            actor_id=actor_id,
            action="import.completed",
            entity_type="import_job",
            entity_id=job.id,
            details={
                "filename": filename,
                "rows_total": job.rows_total,
                "rows_success": job.rows_success,
                "rows_error": job.rows_error,
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        # Фиксируем неуспешное задание отдельной транзакцией; исходный файл остаётся
        # доступен для диагностики и управляемого удаления по retention-политике.
        job = ImportJob(
            id=job.id,
            client_id=client_id,
            filename=filename,
            source=detected,
            storage_key=key,
            status=STATUS_ERROR,
            error=str(exc)[:2000],
        )
        db.add(job)
        audit_service.record(
            db,
            client_id=client_id,
            actor_id=actor_id,
            action="import.failed",
            entity_type="import_job",
            entity_id=job.id,
            details={"filename": filename, "error": str(exc)[:500]},
        )
        db.commit()
        raise

    return ImportCommitOut(
        job_id=job.id,
        source=detected,
        rows_total=job.rows_total,
        cards_created=job.cards_created,
        rows_success=job.rows_success,
        rows_error=job.rows_error,
    )


def list_jobs(db: Session, client_id: str, limit: int = 50) -> list[ImportJob]:
    stmt = (
        select(ImportJob)
        .where(ImportJob.client_id == client_id)
        .order_by(ImportJob.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def list_row_results(db: Session, client_id: str, job_id: str) -> list[ImportRowResult]:
    job = db.get(ImportJob, job_id)
    if job is None or job.client_id != client_id:
        raise NotFoundError("Импорт не найден.")
    stmt = (
        select(ImportRowResult)
        .where(ImportRowResult.client_id == client_id, ImportRowResult.job_id == job_id)
        .order_by(ImportRowResult.row_number)
    )
    return list(db.scalars(stmt))


def error_report(
    db: Session,
    client_id: str,
    job_id: str,
    actor_id: str | None = None,
) -> bytes:
    rows = list_row_results(db, client_id, job_id)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["row", "status", "card_id", "field", "code", "message"])
    for row in rows:
        if not row.errors:
            continue
        for error in row.errors:
            writer.writerow(
                [_csv_safe(value) for value in [
                    row.row_number,
                    row.status,
                    row.card_id or "",
                    error.get("field") or "",
                    error.get("code") or "",
                    error.get("message") or "",
                ]]
            )
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="import.error_report_downloaded",
        entity_type="import_job",
        entity_id=job_id,
        details={"reported_rows": sum(1 for row in rows if row.errors)},
    )
    db.commit()
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def list_profiles(db: Session, client_id: str) -> list[MappingProfile]:
    stmt = (
        select(MappingProfile)
        .where(MappingProfile.client_id == client_id)
        .order_by(MappingProfile.name)
    )
    return list(db.scalars(stmt))


def get_profile(db: Session, client_id: str, profile_id: str | None) -> MappingProfile | None:
    if not profile_id:
        return None
    profile = db.get(MappingProfile, profile_id)
    if profile is None or profile.client_id != client_id:
        raise NotFoundError("Профиль сопоставления не найден.")
    return profile


def create_profile(
    db: Session, client_id: str, data: MappingProfileIn, actor_id: str | None = None
) -> MappingProfile:
    _validate_mapping(data.mapping)
    profile = MappingProfile(client_id=client_id, **data.model_dump())
    db.add(profile)
    try:
        db.flush()
        audit_service.record(
            db,
            client_id=client_id,
            actor_id=actor_id,
            action="mapping_profile.created",
            entity_type="mapping_profile",
            entity_id=profile.id,
            after=audit_service.snapshot(profile),
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Профиль с таким названием уже существует.") from exc
    db.refresh(profile)
    return profile


def delete_profile(
    db: Session, client_id: str, profile_id: str, actor_id: str | None = None
) -> None:
    profile = get_profile(db, client_id, profile_id)
    assert profile is not None
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="mapping_profile.deleted",
        entity_type="mapping_profile",
        entity_id=profile.id,
        before=audit_service.snapshot(profile),
    )
    db.delete(profile)
    db.commit()
