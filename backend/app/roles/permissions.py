from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Chatter, Project, User

ADMIN_ROLES = {"admin"}
STAFF_ROLES = {"admin", "manager", "developer", "staff"}
KNOWN_ROLES = ("admin", "manager", "developer", "staff", "customer")


def role_names(user: User) -> set[str]:
    return {role.name for role in user.roles}


def is_admin(user: User) -> bool:
    return bool(role_names(user) & ADMIN_ROLES)


def require_roles(user: User, allowed: set[str]) -> None:
    if not role_names(user) & allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def can_access_project(user: User, project: Project) -> bool:
    if is_admin(user):
        return True
    if project.manager_id == user.id or project.customer_id == user.id:
        return True
    return any(member.id == user.id for member in project.members)


def can_access_chatter(user: User, chatter: Chatter) -> bool:
    if is_admin(user):
        return True
    if chatter.created_by_id == user.id:
        return True
    if any(member.id == user.id for member in chatter.members):
        return True
    return bool(chatter.project and can_access_project(user, chatter.project))


def assert_project_access(user: User, project: Project) -> None:
    if not can_access_project(user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project is not assigned to this user")


def assert_chatter_access(user: User, chatter: Chatter) -> None:
    if not can_access_chatter(user, chatter):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chatter is not assigned to this user")


def assign_roles(db: Session, user: User, names: list[str]) -> None:
    from app.models import Role

    roles = db.query(Role).filter(Role.name.in_(names)).all()
    user.roles = roles
