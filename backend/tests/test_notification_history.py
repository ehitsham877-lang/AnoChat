import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base
from app.models import Notification, Role, User
from app.notifications.routes import list_notification_history, mark_notification_read, unread_count


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


def add_user(db, name="User", email="user@example.com"):
    role = db.query(Role).filter(Role.name == "developer").first()
    if not role:
        role = Role(name="developer", description="Developer role")
        db.add(role)
        db.flush()
    user = User(name=name, login=email, email=email, hashed_password="x", roles=[role])
    db.add(user)
    db.flush()
    return user


def test_notification_history_returns_read_and_unread_items(db):
    user = add_user(db)
    db.add_all([
        Notification(user_id=user.id, title="Unread", body="New item", is_read=False),
        Notification(user_id=user.id, title="Read", body="Old item", is_read=True),
    ])
    db.commit()

    all_rows = list_notification_history(status="all", limit=25, offset=0, db=db, current_user=user)
    unread_rows = list_notification_history(status="unread", limit=25, offset=0, db=db, current_user=user)
    count = unread_count(db=db, current_user=user)

    assert {item.title for item in all_rows} == {"Unread", "Read"}
    assert [item.title for item in unread_rows] == ["Unread"]
    assert count.unread_count == 1


def test_mark_notification_read_only_updates_current_user_item(db):
    user = add_user(db)
    other = add_user(db, "Other", "other@example.com")
    own = Notification(user_id=user.id, title="Own", is_read=False)
    other_notification = Notification(user_id=other.id, title="Other", is_read=False)
    db.add_all([own, other_notification])
    db.commit()

    updated = mark_notification_read(own.id, db=db, current_user=user)

    assert updated.is_read is True
    assert unread_count(db=db, current_user=user).unread_count == 0
    with pytest.raises(HTTPException) as exc:
        mark_notification_read(other_notification.id, db=db, current_user=user)
    assert exc.value.status_code == 404
