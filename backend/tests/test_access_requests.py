import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.access_requests.routes import approve_access_request, create_access_request, reject_access_request
from app.database import Base
from app.models import Chatter, Project, Role, User
from app.roles.permissions import can_access_project
from app.schemas import AccessRequestCreate


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


def add_project(db, name="Private Project"):
    project = Project(name=name)
    db.add(project)
    db.flush()
    return project


def test_access_request_can_be_approved_for_project(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    requester = add_user(db, "Developer", "dev@example.com")
    project = add_project(db)
    chatter = Chatter(name="Project Chatter", project_id=project.id, created_by_id=admin.id)
    db.add(chatter)
    db.commit()

    request = create_access_request(
        AccessRequestCreate(resource_type="project", project_id=project.id, message="Need project files"),
        db=db,
        current_user=requester,
    )
    approved = approve_access_request(request.id, db=db, current_user=admin)

    db.refresh(project)
    db.refresh(chatter)
    assert approved.status == "approved"
    assert can_access_project(requester, project) is True
    assert requester.id in [member.id for member in chatter.members]


def test_duplicate_pending_access_request_is_blocked(db):
    requester = add_user(db, "Developer", "dev@example.com")
    project = add_project(db)
    db.commit()

    payload = AccessRequestCreate(resource_type="project", project_id=project.id)
    create_access_request(payload, db=db, current_user=requester)

    with pytest.raises(HTTPException) as exc:
        create_access_request(payload, db=db, current_user=requester)

    assert exc.value.status_code == 409


def test_rejected_access_request_does_not_grant_project_access(db):
    admin = add_user(db, "Admin", "admin@example.com", "admin")
    requester = add_user(db, "Developer", "dev@example.com")
    project = add_project(db)
    db.commit()

    request = create_access_request(
        AccessRequestCreate(resource_type="project", project_id=project.id),
        db=db,
        current_user=requester,
    )
    rejected = reject_access_request(request.id, db=db, current_user=admin)

    db.refresh(project)
    assert rejected.status == "rejected"
    assert can_access_project(requester, project) is False
