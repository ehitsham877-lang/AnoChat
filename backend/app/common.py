from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Chatter, Project, Role, User


def get_or_404(db: Session, model, item_id: int):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} not found")
    return item


def users_by_ids(db: Session, ids: list[int]) -> list[User]:
    return db.query(User).filter(User.id.in_(ids)).all() if ids else []


def ensure_roles(db: Session, names: list[str] | tuple[str, ...]) -> list[Role]:
    roles = []
    for name in names:
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=f"{name.title()} role")
            db.add(role)
            db.flush()
        roles.append(role)
    return roles


def set_project_members(db: Session, project: Project, ids: list[int]) -> None:
    project.members = users_by_ids(db, ids)


def set_chatter_members(db: Session, chatter: Chatter, ids: list[int]) -> None:
    chatter.members = users_by_ids(db, ids)
