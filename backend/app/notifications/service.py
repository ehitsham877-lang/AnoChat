from sqlalchemy.orm import Session

from app.models import Notification


def create_notification(db: Session, user_id: int, title: str, body: str | None = None) -> Notification:
    notification = Notification(user_id=user_id, title=title, body=body)
    db.add(notification)
    db.flush()
    return notification


def notify_users(db: Session, user_ids: list[int], title: str, body: str | None = None) -> None:
    seen: set[int] = set()
    for user_id in user_ids:
        if user_id and user_id not in seen:
            seen.add(user_id)
            create_notification(db, user_id, title, body)
