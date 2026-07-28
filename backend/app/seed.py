"""Демо-данные для прототипа: клиент, пользователи, карточки.

Запуск: uv run python -m app.seed
Идемпотентно: повторный запуск не создаёт дубликаты пользователей.

Логины после сидинга:
  client@nk-lab.ru   / password  — сотрудник клиента (импортёр одежды)
  operator@nk-lab.ru / password  — оператор каталога НК-ЛАБ
"""

from __future__ import annotations

from app.config import settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.modules.auth import repository as auth_repo
from app.modules.auth.models import ROLE_CLIENT, ROLE_OPERATOR, Client, User

# импорт моделей для регистрации метаданных
from app.modules.catalog import models as _catalog  # noqa: F401
from app.modules.catalog.schemas import BuildFromVariationsIn, CardCreateIn
from app.modules.catalog.service import build_from_variations, create_card, validate_card
from app.modules.import_data import models as _import  # noqa: F401
from app.modules.operator import models as _operator  # noqa: F401


def run() -> None:
    if not settings.demo_accounts_enabled:
        raise RuntimeError(
            "Создание демо-аккаунтов отключено настройкой DEMO_ACCOUNTS_ENABLED."
        )
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if auth_repo.get_user_by_email(db, "client@nk-lab.ru"):
            print("Демо-данные уже существуют — пропускаю.")
            return

        client = auth_repo.create_client(db, Client(name="Демо Импорт Одежды", inn="7701234567"))
        auth_repo.create_user(
            db,
            User(
                email="client@nk-lab.ru",
                hashed_password=hash_password("password"),
                full_name="Иван Клиентов",
                role=ROLE_CLIENT,
                client_id=client.id,
            ),
        )
        auth_repo.create_user(
            db,
            User(
                email="operator@nk-lab.ru",
                hashed_password=hash_password("password"),
                full_name="Ольга Операторова",
                role=ROLE_OPERATOR,
                client_id=client.id,
            ),
        )
        db.commit()

        # Модель футболки: 3 цвета × 3 размера = 9 карточек-черновиков.
        build_from_variations(
            db,
            client.id,
            BuildFromVariationsIn(
                name="Футболка базовая",
                base_vendor_code="TSHIRT-BASIC",
                category_code="6109",
                common_attributes={
                    "item_type": "футболка",
                    "composition": "хлопок 100%",
                    "age_group": "взрослая",
                    "brand": "DemoWear",
                    "country": "Россия",
                },
                rd_data={
                    "type": "declaration",
                    "number": "ЕАЭС N RU Д-RU.РА01.В.12345/26",
                    "date": "2026-02-01",
                    "valid_until": "2029-02-01",
                },
                colors=["чёрный", "белый", "синий"],
                sizes=["S", "M", "L"],
                genders=["мужской"],
            ),
        )

        # Одна валидная карточка с корректным GTIN — пройдёт валидацию и публикацию.
        valid = create_card(
            db,
            client.id,
            CardCreateIn(
                name="Джемпер шерстяной",
                vendor_code="JMP-WOOL-GREY-M",
                category_code="6110",
                gtin="4600000000015",  # корректная контрольная цифра GS1
                attributes={
                    "item_type": "джемпер",
                    "composition": "шерсть 80%, акрил 20%",
                    "size": "M",
                    "color": "серый",
                    "gender": "женский",
                    "age_group": "взрослая",
                },
                rd_data={
                    "type": "certificate",
                    "number": "ЕАЭС RU С-RU.РА01.В.00987/26",
                    "date": "2026-01-15",
                    "valid_until": "2028-01-15",
                },
            ),
        )
        validate_card(db, client.id, valid.id)

        # Карточка с ошибками: нет части атрибутов и нет РД — покажет работу валидатора.
        broken = create_card(
            db,
            client.id,
            CardCreateIn(
                name="Куртка демисезонная",
                vendor_code="JCK-DEMI-RED-L",
                category_code="6203",
                gtin="123",  # неверный GTIN
                attributes={"item_type": "куртка", "color": "красный", "size": "L"},
                rd_data={},
            ),
        )
        validate_card(db, client.id, broken.id)

        print("Демо-данные созданы.")
        print("  client@nk-lab.ru / password  (клиент)")
        print("  operator@nk-lab.ru / password (оператор)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
