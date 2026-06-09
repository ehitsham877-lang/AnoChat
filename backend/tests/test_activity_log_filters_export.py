import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.activity_logs.routes import export_activity_logs, list_activity_logs
from app.database import Base
from app.models import ActivityLog, Chatter, LoginAudit, Project, Role, User


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


def add_user(db, name="Admin", email="admin@example.com", role_name="admin"):
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name, description=f"{role_name.title()} role")
        db.add(role)
        db.flush()
    user = User(name=name, login=email, email=email, hashed_password="x", roles=[role])
    db.add(user)
    db.flush()
    return user


def test_activity_logs_support_type_status_entity_and_date_filters(db):
    admin = add_user(db)
    project = Project(name="Filtered Project")
    other_project = Project(name="Other Project")
    db.add_all([project, other_project])
    db.flush()
    chatter = Chatter(name="Filtered Chatter", project_id=project.id, created_by_id=admin.id)
    db.add(chatter)
    db.flush()
    now = datetime.utcnow()
    db.add_all([
        ActivityLog(
            user_id=admin.id,
            project_id=project.id,
            chatter_id=chatter.id,
            activity_type="message_sent",
            description="Important chatter message",
            status="success",
            created_at=now,
        ),
        ActivityLog(
            user_id=admin.id,
            project_id=other_project.id,
            activity_type="project_updated",
            description="Old project update",
            status="failed",
            created_at=now - timedelta(days=5),
        ),
        LoginAudit(login=admin.email, user_id=admin.id, status="success", created_at=now),
    ])
    db.commit()

    rows = list_activity_logs(
        q="important",
        type="message",
        status="success",
        user_id=admin.id,
        project_id=project.id,
        chatter_id=chatter.id,
        date_from=date.today(),
        date_to=date.today(),
        limit=100,
        db=db,
        current_user=admin,
    )

    assert len(rows) == 1
    assert rows[0]["activity_type"] == "message_sent"
    assert rows[0]["project_name"] == project.name
    assert rows[0]["chatter_name"] == chatter.name
    assert rows[0]["user_name"] == admin.name


def test_activity_log_export_returns_csv_response(db):
    admin = add_user(db)
    db.add(ActivityLog(user_id=admin.id, activity_type="user_updated", description="Role changed", status="success"))
    db.commit()

    response = export_activity_logs(
        q=None,
        type="all",
        status="all",
        user_id=None,
        project_id=None,
        chatter_id=None,
        date_from=None,
        date_to=None,
        db=db,
        current_user=admin,
    )

    assert response.media_type == "text/csv"
    assert "anochat-audit-logs.csv" in response.headers["content-disposition"]
