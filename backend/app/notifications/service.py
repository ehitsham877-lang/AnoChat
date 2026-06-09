import json
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmailLog, Notification, NotificationPreference, User, WebPushSubscription

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - optional until dependency is installed
    WebPushException = Exception
    webpush = None

PUSH_CHATTER_MESSAGE = "chatter_message"
PUSH_WORKSPACE_UPDATE = "workspace_update"


def get_or_create_preferences(db: Session, user_id: int) -> NotificationPreference:
    preferences = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
    if not preferences:
        preferences = NotificationPreference(user_id=user_id)
        db.add(preferences)
        db.flush()
    return preferences


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    body: str | None = None,
    *,
    push_category: str = PUSH_WORKSPACE_UPDATE,
    action_url: str = "/frontend/index.html",
) -> Notification:
    notification = Notification(user_id=user_id, title=title, body=body)
    db.add(notification)
    db.flush()
    send_push_notification(db, user_id, title, body, push_category=push_category, action_url=action_url)
    send_email_alert(db, user_id, title, body, category=push_category, action_url=action_url)
    return notification


def notify_users(
    db: Session,
    user_ids: list[int],
    title: str,
    body: str | None = None,
    *,
    push_category: str = PUSH_WORKSPACE_UPDATE,
    action_url: str = "/frontend/index.html",
) -> None:
    seen: set[int] = set()
    for user_id in user_ids:
        if user_id and user_id not in seen:
            seen.add(user_id)
            create_notification(db, user_id, title, body, push_category=push_category, action_url=action_url)


def push_configured() -> bool:
    settings = get_settings()
    return bool(webpush and settings.vapid_public_key and settings.vapid_private_key)


def email_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host and settings.smtp_from_email)


def send_push_notification(
    db: Session,
    user_id: int,
    title: str,
    body: str | None,
    *,
    push_category: str,
    action_url: str,
) -> None:
    if not push_configured():
        return
    preferences = get_or_create_preferences(db, user_id)
    if not preferences.browser_push_enabled:
        return
    if push_category == PUSH_CHATTER_MESSAGE and not preferences.push_chatter_messages:
        return
    if push_category == PUSH_WORKSPACE_UPDATE and not preferences.push_workspace_updates:
        return
    subscriptions = (
        db.query(WebPushSubscription)
        .filter(WebPushSubscription.user_id == user_id, WebPushSubscription.active.is_(True))
        .all()
    )
    if not subscriptions:
        return
    settings = get_settings()
    payload = json.dumps({
        "title": title,
        "body": body or "",
        "url": action_url,
        "tag": f"anochat-{push_category}",
    })
    claims = {"sub": f"mailto:{settings.vapid_claims_email}"}
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims=claims,
                timeout=2,
                ttl=60,
            )
        except WebPushException as exc:
            if getattr(getattr(exc, "response", None), "status_code", None) in {404, 410}:
                subscription.active = False
        except Exception:
            continue


def send_email_alert(
    db: Session,
    user_id: int,
    title: str,
    body: str | None,
    *,
    category: str,
    action_url: str,
) -> None:
    preferences = get_or_create_preferences(db, user_id)
    if not preferences.email_alerts_enabled:
        return
    if category == PUSH_CHATTER_MESSAGE and not preferences.email_chatter_messages:
        return
    if category == PUSH_WORKSPACE_UPDATE and not preferences.email_workspace_updates:
        return
    user = db.get(User, user_id)
    if not user or not user.active or not user.email:
        return

    settings = get_settings()
    sender = settings.smtp_from_email or settings.smtp_username
    log = EmailLog(
        user_id=user.id,
        email_from=sender or None,
        email_to=user.email,
        subject=title,
        body_excerpt=(body or "")[:2000],
        status="skipped",
    )
    db.add(log)
    db.flush()

    if not email_configured():
        log.status = "skipped_smtp_not_configured"
        return

    message = EmailMessage()
    message["Subject"] = title
    message["From"] = sender
    message["To"] = user.email
    message.set_content(
        "\n".join([
            body or title,
            "",
            f"Open AnoChat: {action_url}",
            "",
            "You are receiving this because email alerts are enabled for your AnoChat account.",
        ])
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        log.status = "sent"
    except Exception as exc:
        log.status = "failed"
        log.body_excerpt = f"{(body or '')[:1800]}\n\nEmail error: {str(exc)[:180]}"
