import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base
from app.models import EmailLog, NotificationPreference, Role, User, WebPushSubscription
from app.notifications import service
from app.notifications.service import PUSH_CHATTER_MESSAGE, create_notification, get_or_create_preferences


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


def add_user(db):
    role = Role(name="developer", description="Developer role")
    user = User(name="Dev User", login="dev@example.com", email="dev@example.com", hashed_password="x", roles=[role])
    db.add_all([role, user])
    db.commit()
    db.refresh(user)
    return user


def test_default_notification_preferences_are_created(db):
    user = add_user(db)

    preferences = get_or_create_preferences(db, user.id)
    db.commit()

    assert preferences.browser_push_enabled is False
    assert preferences.push_chatter_messages is True
    assert preferences.push_workspace_updates is True
    assert preferences.email_alerts_enabled is False
    assert preferences.email_chatter_messages is True
    assert preferences.email_workspace_updates is True


def test_push_sends_only_when_user_enabled_preferences(db, monkeypatch):
    user = add_user(db)
    db.add(NotificationPreference(user_id=user.id, browser_push_enabled=True, push_chatter_messages=True))
    db.add(WebPushSubscription(user_id=user.id, endpoint="https://push.example/1", p256dh="key", auth="auth"))
    db.commit()
    sent = []
    settings = service.get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "public")
    monkeypatch.setattr(settings, "vapid_private_key", "private")
    monkeypatch.setattr(settings, "vapid_claims_email", "admin@example.com")
    monkeypatch.setattr(service, "webpush", lambda **kwargs: sent.append(kwargs))

    create_notification(db, user.id, "New message", "Hello", push_category=PUSH_CHATTER_MESSAGE)

    assert len(sent) == 1
    assert sent[0]["subscription_info"]["endpoint"] == "https://push.example/1"


def test_push_respects_disabled_chatter_preference(db, monkeypatch):
    user = add_user(db)
    db.add(NotificationPreference(user_id=user.id, browser_push_enabled=True, push_chatter_messages=False))
    db.add(WebPushSubscription(user_id=user.id, endpoint="https://push.example/1", p256dh="key", auth="auth"))
    db.commit()
    sent = []
    settings = service.get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "public")
    monkeypatch.setattr(settings, "vapid_private_key", "private")
    monkeypatch.setattr(service, "webpush", lambda **kwargs: sent.append(kwargs))

    create_notification(db, user.id, "New message", "Hello", push_category=PUSH_CHATTER_MESSAGE)

    assert sent == []


def test_email_alert_is_skipped_when_preference_disabled(db):
    user = add_user(db)

    create_notification(db, user.id, "New message", "Hello", push_category=PUSH_CHATTER_MESSAGE)

    assert db.query(EmailLog).count() == 0


def test_email_alert_logs_when_smtp_is_not_configured(db):
    user = add_user(db)
    db.add(NotificationPreference(user_id=user.id, email_alerts_enabled=True, email_chatter_messages=True))
    db.commit()

    create_notification(db, user.id, "New message", "Hello", push_category=PUSH_CHATTER_MESSAGE)

    log = db.query(EmailLog).one()
    assert log.email_to == user.email
    assert log.status == "skipped_smtp_not_configured"


def test_email_alert_sends_when_configured(db, monkeypatch):
    user = add_user(db)
    db.add(NotificationPreference(user_id=user.id, email_alerts_enabled=True, email_chatter_messages=True))
    db.commit()
    sent = []
    settings = service.get_settings()
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_from_email", "alerts@example.com")
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "smtp_use_tls", True)

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            sent.append(("tls", self.host, self.port))

        def send_message(self, message):
            sent.append(("message", message["To"], message["Subject"]))

    monkeypatch.setattr(service.smtplib, "SMTP", FakeSMTP)

    create_notification(db, user.id, "New message", "Hello", push_category=PUSH_CHATTER_MESSAGE)

    log = db.query(EmailLog).one()
    assert log.status == "sent"
    assert ("message", user.email, "New message") in sent
