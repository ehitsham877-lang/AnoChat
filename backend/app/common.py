from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Chatter, Project, Role, User, chatter_members, project_members


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


def normalized_ids(ids: list[int] | set[int] | None) -> list[int]:
    return list(dict.fromkeys(int(item) for item in (ids or []) if item))


def set_project_members(db: Session, project: Project, ids: list[int], read_only_ids: list[int] | None = None) -> None:
    read_only = set(normalized_ids(read_only_ids))
    all_ids = normalized_ids(list(ids or []) + list(read_only))
    db.flush()
    db.execute(project_members.delete().where(project_members.c.project_id == project.id))
    if all_ids:
        db.execute(
            project_members.insert(),
            [{"project_id": project.id, "user_id": user_id, "is_read_only": user_id in read_only} for user_id in all_ids],
        )
    db.expire(project, ["members"])


def set_chatter_members(db: Session, chatter: Chatter, ids: list[int], read_only_ids: list[int] | None = None) -> None:
    read_only = set(normalized_ids(read_only_ids))
    all_ids = normalized_ids(list(ids or []) + list(read_only))
    db.flush()
    db.execute(chatter_members.delete().where(chatter_members.c.chatter_id == chatter.id))
    if all_ids:
        db.execute(
            chatter_members.insert(),
            [{"chatter_id": chatter.id, "user_id": user_id, "is_read_only": user_id in read_only} for user_id in all_ids],
        )
    db.expire(chatter, ["members"])


def sync_project_members_from_chatter(db: Session, chatter: Chatter, member_ids: list[int], read_only_member_ids: list[int] | None = None) -> None:
    if not chatter.project_id:
        return
    project = db.get(Project, chatter.project_id)
    if not project:
        return
    normal_chatter_ids = set(normalized_ids(member_ids))
    read_only_chatter_ids = set(normalized_ids(read_only_member_ids))
    project_read_only_ids = set(read_only_project_member_ids(db, project.id))
    project_member_ids = {member.id for member in project.members}
    merged_member_ids = project_member_ids | normal_chatter_ids | read_only_chatter_ids
    merged_read_only_ids = (project_read_only_ids | read_only_chatter_ids) - normal_chatter_ids
    set_project_members(db, project, list(merged_member_ids), list(merged_read_only_ids))


def sync_project_members_from_linked_chatters(db: Session, project: Project) -> bool:
    if not project or not project.id:
        return False
    chatter_ids = [
        row[0]
        for row in db.query(Chatter.id)
        .filter(Chatter.project_id == project.id, Chatter.active.is_(True))
        .all()
    ]
    if not chatter_ids:
        return False

    current_rows = db.execute(project_members.select().where(project_members.c.project_id == project.id)).all()
    current_state = {row.user_id: bool(row.is_read_only) for row in current_rows}
    normal_ids = {user_id for user_id, is_read_only in current_state.items() if not is_read_only}
    read_only_ids = {user_id for user_id, is_read_only in current_state.items() if is_read_only}
    if project.manager_id:
        normal_ids.add(project.manager_id)
    if project.customer_id:
        normal_ids.add(project.customer_id)

    chatter_rows = db.execute(chatter_members.select().where(chatter_members.c.chatter_id.in_(chatter_ids))).all()
    for row in chatter_rows:
        user_id = int(row.user_id)
        if row.is_read_only:
            read_only_ids.add(user_id)
        else:
            normal_ids.add(user_id)

    read_only_ids -= normal_ids
    desired_ids = normal_ids | read_only_ids
    desired_state = {user_id: user_id in read_only_ids for user_id in desired_ids}
    if current_state == desired_state:
        return False
    set_project_members(db, project, list(desired_ids), list(read_only_ids))
    return True


def read_only_project_member_ids(db: Session, project_id: int) -> list[int]:
    return [
        row[0]
        for row in db.execute(
            project_members.select()
            .with_only_columns(project_members.c.user_id)
            .where(project_members.c.project_id == project_id, project_members.c.is_read_only.is_(True))
        ).all()
    ]


def read_only_chatter_member_ids(db: Session, chatter_id: int) -> list[int]:
    return [
        row[0]
        for row in db.execute(
            chatter_members.select()
            .with_only_columns(chatter_members.c.user_id)
            .where(chatter_members.c.chatter_id == chatter_id, chatter_members.c.is_read_only.is_(True))
        ).all()
    ]
