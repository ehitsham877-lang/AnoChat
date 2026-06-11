import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.chatters.routes import create_chatter, create_message, list_chatters, update_chatter
from app.database import Base
from app.models import Chatter, Project, Role, User
from app.projects.routes import get_project, list_projects, update_project
from app.schemas import ChatterCreate, ChatterUpdate, MessageCreate, ProjectUpdate


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def add_user(db, name, email, role_name="developer"):
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name, description=f"{role_name.title()} role")
        db.add(role)
        db.flush()
    user = User(name=name, login=email, email=email, hashed_password="x", roles=[role])
    db.add(user)
    db.flush()
    return user


def add_project(db, name="Linked Project"):
    project = Project(name=name)
    db.add(project)
    db.flush()
    return project


def test_chatter_create_syncs_members_to_linked_project(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    member = add_user(db, "Member", "member@example.com")
    project = add_project(db)
    db.commit()

    create_chatter(
        ChatterCreate(name="Project chat", project_id=project.id, member_ids=[member.id]),
        db=db,
        current_user=admin,
    )

    db.refresh(project)
    project_member_ids = {user.id for user in project.members}
    assert admin.id in project_member_ids
    assert member.id in project_member_ids


def test_chatter_update_syncs_new_members_to_linked_project(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    first_member = add_user(db, "First", "first@example.com")
    added_member = add_user(db, "Added", "added@example.com")
    project = add_project(db)
    chatter = Chatter(name="Project chat", project_id=project.id, created_by_id=admin.id)
    db.add(chatter)
    db.commit()

    update_chatter(
        chatter.id,
        ChatterUpdate(member_ids=[admin.id, first_member.id, added_member.id]),
        db=db,
        current_user=admin,
    )

    db.refresh(project)
    project_member_ids = {user.id for user in project.members}
    assert {admin.id, first_member.id, added_member.id}.issubset(project_member_ids)


def test_chatter_update_removes_members_from_linked_project(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    kept_member = add_user(db, "Kept", "kept@example.com")
    removed_member = add_user(db, "Removed", "removed@example.com")
    project = add_project(db)
    chatter = Chatter(name="Project chat", project_id=project.id, created_by_id=admin.id)
    db.add(chatter)
    db.flush()
    chatter.members = [admin, kept_member, removed_member]
    project.members = [admin, kept_member, removed_member]
    db.commit()

    update_chatter(
        chatter.id,
        ChatterUpdate(member_ids=[admin.id, kept_member.id]),
        db=db,
        current_user=admin,
    )

    db.refresh(project)
    project_member_ids = {user.id for user in project.members}
    assert project_member_ids == {admin.id, kept_member.id}
    assert list_projects(db=db, current_user=removed_member) == []


def test_chatter_list_repairs_stale_project_members_before_visibility_filter(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    kept_member = add_user(db, "Kept", "kept@example.com")
    removed_member = add_user(db, "Removed", "removed@example.com")
    project = add_project(db)
    chatter = Chatter(name="Project chat", project_id=project.id, created_by_id=admin.id)
    db.add(chatter)
    db.flush()
    chatter.members = [admin, kept_member]
    project.members = [admin, kept_member, removed_member]
    db.commit()

    visible_chatters = list_chatters(db=db, current_user=removed_member)

    db.refresh(project)
    assert visible_chatters == []
    assert removed_member.id not in {user.id for user in project.members}


def test_project_list_repairs_chatter_only_members_before_visibility_filter(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    added_member = add_user(db, "Added", "added@example.com")
    project = add_project(db)
    chatter = Chatter(name="Project chat", project_id=project.id, created_by_id=admin.id)
    db.add(chatter)
    db.flush()
    chatter.members = [admin, added_member]
    project.members = [admin]
    db.commit()

    visible_projects = list_projects(db=db, current_user=added_member)

    db.refresh(project)
    assert [item.id for item in visible_projects] == [project.id]
    assert added_member.id in {user.id for user in project.members}


def test_project_update_removes_member_from_linked_chatter_and_revokes_session(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    kept_member = add_user(db, "Kept", "kept@example.com")
    removed_member = add_user(db, "Removed", "removed@example.com")
    project = add_project(db)
    chatter = Chatter(name="Project chat", project_id=project.id, created_by_id=admin.id)
    db.add(chatter)
    db.flush()
    project.members = [admin, kept_member, removed_member]
    chatter.members = [admin, kept_member, removed_member]
    db.commit()

    update_project(
        project.id,
        ProjectUpdate(member_ids=[admin.id, kept_member.id]),
        db=db,
        current_user=admin,
    )

    db.refresh(project)
    db.refresh(chatter)
    assert {user.id for user in project.members} == {admin.id, kept_member.id}
    assert {user.id for user in chatter.members} == {admin.id, kept_member.id}
    assert removed_member.active_session_version == 1
    assert list_projects(db=db, current_user=removed_member) == []
    assert list_chatters(db=db, current_user=removed_member) == []
    with pytest.raises(HTTPException) as project_error:
        get_project(project.id, db=db, current_user=removed_member)
    assert project_error.value.status_code == 403
    with pytest.raises(HTTPException) as message_error:
        create_message(chatter.id, MessageCreate(body="Still here?"), db=db, current_user=removed_member)
    assert message_error.value.status_code == 403
