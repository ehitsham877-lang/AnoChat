from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Chatter, Project, User, chatter_members, project_members

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


def require_write_access(user: User) -> None:
    if user.read_only:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only users cannot make changes")


def project_read_only(db: Session, user: User, project: Project) -> bool:
    if user.read_only:
        return True
    if not project or not project.id:
        return False
    return bool(db.execute(
        project_members.select()
        .where(
            project_members.c.project_id == project.id,
            project_members.c.user_id == user.id,
            project_members.c.is_read_only.is_(True),
        )
    ).first())


def chatter_read_only(db: Session, user: User, chatter: Chatter) -> bool:
    if user.read_only:
        return True
    if chatter and chatter.id and db.execute(
        chatter_members.select()
        .where(
            chatter_members.c.chatter_id == chatter.id,
            chatter_members.c.user_id == user.id,
            chatter_members.c.is_read_only.is_(True),
        )
    ).first():
        return True
    return bool(chatter and chatter.project and project_read_only(db, user, chatter.project))


def require_project_write_access(db: Session, user: User, project: Project) -> None:
    if project_read_only(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only project access cannot make changes")


def require_chatter_write_access(db: Session, user: User, chatter: Chatter) -> None:
    if chatter_read_only(db, user, chatter):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only chatter access cannot make changes")


def can_access_project(user: User, project: Project) -> bool:
    if is_admin(user):
        return True
    if project.manager_id == user.id or project.customer_id == user.id:
        return True
    return any(member.id == user.id for member in project.members)


def can_access_chatter(user: User, chatter: Chatter) -> bool:
    if is_admin(user):
        return True
    if chatter.created_by_id == user.id and not chatter.project_id:
        return True
    if any(member.id == user.id for member in chatter.members):
        return True
    if chatter.project_id and chatter.members:
        return False
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
