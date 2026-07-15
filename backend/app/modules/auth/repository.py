"""Доступ к данным аутентификации."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import Client, User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, user: User) -> User:
    db.add(user)
    db.flush()
    return user


def get_client_by_name(db: Session, name: str) -> Client | None:
    return db.scalar(select(Client).where(Client.name == name))


def create_client(db: Session, client: Client) -> Client:
    db.add(client)
    db.flush()
    return client
