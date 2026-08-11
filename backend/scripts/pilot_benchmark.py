#!/usr/bin/env python3
"""Проверка полного пакетного пути на 300–500 карточках без изменения рабочей БД."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import tempfile
import time


def _csv_payload(rows: int) -> bytes:
    from app.modules.gtin.domain import compute_check_digit

    stream = io.StringIO()
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(
        [
            "Наименование",
            "Артикул",
            "Категория",
            "GTIN",
            "Вид изделия",
            "Цвет",
            "Размер",
            "Пол",
            "Состав",
            "Возрастная группа",
            "Тип РД",
            "Номер РД",
            "Дата РД",
            "Срок действия",
        ]
    )
    colors = ("белый", "чёрный", "синий", "серый", "зелёный")
    sizes = ("XS", "S", "M", "L", "XL")
    for index in range(rows):
        body = f"4601234{index:05d}"
        gtin = f"{body}{compute_check_digit(body)}"
        writer.writerow(
            [
                f"Футболка пилот {index // 25 + 1}",
                f"PILOT-{index + 1:04d}",
                "6109",
                gtin,
                "футболка",
                colors[index % len(colors)],
                sizes[(index // len(colors)) % len(sizes)],
                "унисекс",
                "хлопок 100%",
                "взрослая",
                "declaration",
                f"ЕАЭС N RU Д-PILOT-{index + 1:04d}",
                "2026-01-15",
                "2029-01-15",
            ]
        )
    return stream.getvalue().encode("utf-8-sig")


class _MemoryStorage:
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        return key


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=500)
    args = parser.parse_args()
    if args.rows < 1 or args.rows > 5000:
        parser.error("--rows должен быть от 1 до 5000")

    with tempfile.TemporaryDirectory(prefix="nklab-pilot-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{tmp}/pilot.db"
        os.environ["APP_ENV"] = "test"

        from sqlalchemy import func, select

        from app.database import Base, SessionLocal, engine
        from app.modules.audit import models as _audit  # noqa: F401
        from app.modules.catalog import models as _catalog  # noqa: F401
        from app.modules.catalog.models import Card
        from app.modules.import_data import models as _import_models  # noqa: F401
        from app.modules.import_data import service as import_service
        from app.modules.nk_exchange import models as _exchange  # noqa: F401

        import_service.storage = _MemoryStorage()
        Base.metadata.create_all(bind=engine)
        started = time.perf_counter()
        with SessionLocal() as db:
            result = import_service.commit(
                db,
                client_id="pilot-benchmark",
                filename="pilot-500.csv",
                source="csv",
                content=_csv_payload(args.rows),
                actor_id=None,
            )
            statuses = dict(
                db.execute(
                    select(Card.status, func.count())
                    .where(Card.client_id == "pilot-benchmark")
                    .group_by(Card.status)
                ).all()
            )
        elapsed = time.perf_counter() - started

    report = {
        "rows": result.rows_total,
        "cards_created": result.cards_created,
        "rows_success": result.rows_success,
        "rows_error": result.rows_error,
        "statuses": statuses,
        "elapsed_seconds": round(elapsed, 3),
        "cards_per_second": round(result.cards_created / elapsed, 1),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if result.cards_created == args.rows and result.rows_error == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
