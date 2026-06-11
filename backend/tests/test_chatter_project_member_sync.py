import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.chatters.routes import create_chatter, create_message, list_chatters, update_chatter
from app.database import Base
from app.models import Chatter, Notification, Project, Role, User
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
    assert [item.id for item in list_projects(db=db, current_user=added_member)] == [project.id]


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
    assert db.query(Notification).filter(Notification.user_id == removed_member.id, Notification.title == "Removed from chatter").count() == 1


def test_chatter_update_replaces_project_members_even_with_stale_linked_chatter(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    kept_member = add_user(db, "Kept", "kept@example.com")
    removed_member = add_user(db, "Removed", "removed@example.com")
    project = add_project(db)
    active_chatter = Chatter(name="Primary project chat", project_id=project.id, created_by_id=admin.id)
    stale_chatter = Chatter(name="Stale project chat", project_id=project.id, created_by_id=admin.id)
    db.add_all([active_chatter, stale_chatter])
    db.flush()
    active_chatter.members = [admin, kept_member, removed_member]
    stale_chatter.members = [admin, removed_member]
    project.members = [admin, kept_member, removed_member]
    db.commit()

    update_chatter(
        active_chatter.id,
        ChatterUpdate(member_ids=[admin.id, kept_member.id]),
        db=db,
        current_user=admin,
    )

    db.refresh(project)
    db.refresh(active_chatter)
    assert {user.id for user in active_chatter.members} == {admin.id, kept_member.id}
    assert {user.id for user in project.members} == {admin.id, kept_member.id}
    assert list_projects(db=db, current_user=removed_member) == []
    assert list_chatters(db=db, current_user=removed_member) == []


def test_stale_project_members_do_not_grant_chatter_access(db):
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
    assert removed_member.id in {user.id for user in project.members}


def test_project_update_removes_member_from_linked_chatter_and_blocks_access(db):
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
    assert removed_member.active_session_version == 0
    assert list_projects(db=db, current_user=removed_member) == []
    assert list_chatters(db=db, current_user=removed_member) == []
    with pytest.raises(HTTPException) as project_error:
        get_project(project.id, db=db, current_user=removed_member)
    assert project_error.value.status_code == 403
    with pytest.raises(HTTPException) as message_error:
        create_message(chatter.id, MessageCreate(body="Still here?"), db=db, current_user=removed_member)
    assert message_error.value.status_code == 403


def test_linked_chatter_creator_loses_access_when_removed(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    creator = add_user(db, "Creator", "creator@example.com")
    kept_member = add_user(db, "Kept", "kept@example.com")
    project = add_project(db)
    chatter = Chatter(name="Project chat", project_id=project.id, created_by_id=creator.id)
    db.add(chatter)
    db.flush()
    project.members = [creator, kept_member]
    chatter.members = [creator, kept_member]
    db.commit()

    update_chatter(
        chatter.id,
        ChatterUpdate(member_ids=[kept_member.id]),
        db=db,
        current_user=admin,
    )

    db.refresh(project)
    db.refresh(chatter)
    assert {user.id for user in project.members} == {kept_member.id}
    assert {user.id for user in chatter.members} == {kept_member.id}
    assert creator.active_session_version == 0
    assert list_projects(db=db, current_user=creator) == []
    assert list_chatters(db=db, current_user=creator) == []
    with pytest.raises(HTTPException) as message_error:
        create_message(chatter.id, MessageCreate(body="I made this"), db=db, current_user=creator)
    assert message_error.value.status_code == 403
