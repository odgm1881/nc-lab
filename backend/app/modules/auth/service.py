"""Сценарии аутентификации: регистрация и вход."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.audit import service as audit_service
from app.modules.auth import repository as repo
from app.modules.auth.models import ROLE_CLIENT, Client, User
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut

# Валидный bcrypt-хеш используется только для одинаковой стоимости проверки,
# когда email не найден. Это не пароль какого-либо пользователя.
_DUMMY_PASSWORD_HASH = "$2b$12$LknBt0c4ad/rYarHPuR4S.0AsfEGYPD1v5kyS1k.gVGXen0B4Rj/S"


def register(db: Session, data: RegisterIn) -> User:
    if repo.get_user_by_email(db, data.email):
        raise ConflictError("Пользователь с таким email уже существует.")

    # Публичная регистрация всегда создаёт нового тенанта. Присоединение по одному
    # лишь совпавшему названию организации позволяло попасть в чужой client_id.
    client = repo.create_client(db, Client(name=data.client_name, inn=data.inn))

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=ROLE_CLIENT,
        client_id=client.id,
    )
    repo.create_user(db, user)
    audit_service.record(
        db,
        client_id=client.id,
        actor_id=user.id,
        action="auth.registered",
        entity_type="user",
        entity_id=user.id,
        after={"email": user.email, "role": user.role, "client_id": user.client_id},
    )
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, data: LoginIn) -> TokenOut:
    user = repo.get_user_by_email(db, data.email)
    password_hash = user.hashed_password if user is not None else _DUMMY_PASSWORD_HASH
    password_ok = verify_password(data.password, password_hash)
    if user is None or not password_ok:
        audit_service.record(
            db,
            client_id=user.client_id if user is not None else None,
            actor_id=user.id if user is not None else None,
            action="auth.login_failed",
            entity_type="user" if user is not None else "auth",
            entity_id=user.id if user is not None else None,
            details={"email": str(data.email).lower()},
        )
        db.commit()
        raise AuthError("Неверный email или пароль.")
    token = create_access_token(
        subject=user.id, extra={"role": user.role, "client_id": user.client_id}
    )
    audit_service.record(
        db,
        client_id=user.client_id,
        actor_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        details={"email": user.email},
    )
    db.commit()
    return TokenOut(access_token=token)
