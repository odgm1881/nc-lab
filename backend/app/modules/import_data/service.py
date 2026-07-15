"""Сценарии импорта: определить источник, распарсить, нормализовать, создать карточки.

Файл кладём в хранилище (S3/локально), факт импорта — в таблицу ImportJob со
статусом. Создание карточек делегируем catalog.service (модули не лезут в чужие
таблицы напрямую).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.storage import new_key, storage
from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import CardCreateIn
from app.modules.import_data.models import (
    STATUS_DONE,
    STATUS_ERROR,
    ImportJob,
)
from app.modules.import_data.parsers.base import NomenclatureRow, map_rows
from app.modules.import_data.parsers.csv_parser import parse_csv
from app.modules.import_data.parsers.excel import parse_excel
from app.modules.import_data.parsers.onec import parse_onec
from app.modules.import_data.schemas import (
    ImportCommitOut,
    ImportPreviewOut,
    NomenclatureRowOut,
)


def detect_source(filename: str, source: str | None) -> str:
    if source:
        return source
    lower = filename.lower()
    if lower.endswith(".xlsx") or lower.endswith(".xlsm"):
        return "excel"
    if lower.endswith(".csv"):
        return "csv"
    raise DomainError("Не удалось определить формат файла. Укажите source явно.")


def _parse(source: str, content: bytes) -> list[dict]:
    if source == "excel":
        return parse_excel(content)
    if source == "csv":
        return parse_csv(content)
    if source == "onec":
        return parse_onec(content)
    raise DomainError(f"Неизвестный источник импорта: {source}")


def _row_to_schema(row: NomenclatureRow) -> NomenclatureRowOut:
    return NomenclatureRowOut(
        name=row.name,
        vendor_code=row.vendor_code,
        category_code=row.category_code,
        gtin=row.gtin,
        attributes=row.attributes,
        rd_data=row.rd_data,
    )


def preview(filename: str, source: str | None, content: bytes) -> ImportPreviewOut:
    """Распарсить и нормализовать файл без сохранения."""
    detected = detect_source(filename, source)
    rows = map_rows(_parse(detected, content))
    return ImportPreviewOut(
        source=detected,
        rows_total=len(rows),
        rows=[_row_to_schema(r) for r in rows],
    )


def commit(
    db: Session,
    client_id: str,
    filename: str,
    source: str | None,
    content: bytes,
    create_cards: bool = True,
) -> ImportCommitOut:
    """Сохранить файл, создать ImportJob и (опционально) карточки-черновики."""
    detected = detect_source(filename, source)
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
        rows = map_rows(_parse(detected, content))
        job.rows_total = len(rows)
        created = 0
        if create_cards and rows:
            payloads = [
                CardCreateIn(
                    name=r.name,
                    vendor_code=r.vendor_code,
                    category_code=r.category_code,
                    gtin=r.gtin,
                    attributes=r.attributes,
                    rd_data=r.rd_data,
                )
                for r in rows
            ]
            created = catalog_service.create_cards_bulk(db, client_id, payloads)
        job.cards_created = created
        job.status = STATUS_DONE
        db.commit()
    except Exception as exc:  # noqa: BLE001 — фиксируем ошибку в статусе задания
        db.rollback()
        job.status = STATUS_ERROR
        job.error = str(exc)[:2000]
        db.add(job)
        db.commit()
        raise

    return ImportCommitOut(
        job_id=job.id,
        source=detected,
        rows_total=job.rows_total,
        cards_created=job.cards_created,
    )


def list_jobs(db: Session, client_id: str, limit: int = 50) -> list[ImportJob]:
    stmt = (
        select(ImportJob)
        .where(ImportJob.client_id == client_id)
        .order_by(ImportJob.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
