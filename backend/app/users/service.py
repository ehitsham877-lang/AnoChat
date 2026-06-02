from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.common import ensure_roles
from app.models import User
from app.schemas import UserCreate


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        name=payload.name,
        login=payload.login or payload.email,
        email=str(payload.email),
        phone=payload.phone,
        active=payload.active,
        hashed_password=hash_password(payload.password),
        roles=ensure_roles(db, payload.roles or ["customer"]),
    )
    db.add(user)
    db.flush()
    return user
