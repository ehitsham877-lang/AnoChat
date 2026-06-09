import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.activity_logs.service import log_activity
from app.common import set_project_members
from app.database import Base
from app.models import Chatter, Project, Role, User
from app.projects.routes import list_project_activity


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


def test_project_activity_includes_project_and_linked_chatter_logs(db):
    member = add_user(db, "Member", "member@example.com")
    project = Project(name="Timeline")
    db.add(project)
    db.flush()
    chatter = Chatter(name="Timeline Chat", project_id=project.id, created_by_id=member.id)
    db.add(chatter)
    db.flush()
    set_project_members(db, project, [member.id])
    log_activity(db, "project_updated", "Project changed.", member.id, project_id=project.id)
    log_activity(db, "message_sent", "Message sent.", member.id, project_id=project.id, chatter_id=chatter.id)
    log_activity(db, "user_updated", "Someone unrelated.", member.id)
    db.commit()

    rows = list_project_activity(project.id, db=db, current_user=member)

    assert {row["activity_type"] for row in rows} == {"message_sent", "project_updated"}


def test_project_activity_requires_project_access(db):
    outsider = add_user(db, "Outsider", "outsider@example.com")
    project = Project(name="Private")
    db.add(project)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        list_project_activity(project.id, db=db, current_user=outsider)

    assert exc.value.status_code == 403
