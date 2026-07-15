"""Сценарии аутентификации: регистрация и вход."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth import repository as repo
from app.modules.auth.models import ROLE_CLIENT, Client, User
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut


def register(db: Session, data: RegisterIn) -> User:
    if repo.get_user_by_email(db, data.email):
        raise ConflictError("Пользователь с таким email уже существует.")

    client = repo.get_client_by_name(db, data.client_name)
    if client is None:
        client = repo.create_client(db, Client(name=data.client_name, inn=data.inn))

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=ROLE_CLIENT,
        client_id=client.id,
    )
    repo.create_user(db, user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, data: LoginIn) -> TokenOut:
    user = repo.get_user_by_email(db, data.email)
    if user is None or not verify_password(data.password, user.hashed_password):
        raise AuthError("Неверный email или пароль.")
    token = create_access_token(
        subject=user.id, extra={"role": user.role, "client_id": user.client_id}
    )
    return TokenOut(access_token=token)
