from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import Notification, User, WebPushSubscription
from app.notifications.service import get_or_create_preferences
from app.rate_limit import sensitive_action_rate_limit_dependency
from app.schemas import (
    NotificationOut,
    NotificationCountOut,
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
    PushConfigOut,
    PushSubscriptionIn,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
settings = get_settings()


@router.get("", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .order_by(Notification.created_at.desc())
        .limit(25)
        .all()
    )


@router.get("/history", response_model=list[NotificationOut])
def list_notification_history(
    status: str = Query("all", pattern="^(all|unread|read)$"),
    limit: int = Query(100, ge=1, le=250),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if status == "unread":
        query = query.filter(Notification.is_read.is_(False))
    elif status == "read":
        query = query.filter(Notification.is_read.is_(True))
    return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/unread-count", response_model=NotificationCountOut)
def unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return NotificationCountOut(
        unread_count=db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return {"ok": True}


@router.get("/push-config", response_model=PushConfigOut)
def push_config():
    enabled = bool(settings.vapid_public_key and settings.vapid_private_key)
    return PushConfigOut(enabled=enabled, public_key=settings.vapid_public_key or None)


@router.get("/preferences", response_model=NotificationPreferenceOut)
def get_preferences(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    preferences = get_or_create_preferences(db, current_user.id)
    db.commit()
    db.refresh(preferences)
    return preferences


@router.put("/preferences", response_model=NotificationPreferenceOut, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def update_preferences(
    payload: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preferences = get_or_create_preferences(db, current_user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(preferences, key, value)
    db.commit()
    db.refresh(preferences)
    return preferences


@router.post("/subscriptions", dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def save_subscription(
    payload: PushSubscriptionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = db.query(WebPushSubscription).filter(WebPushSubscription.endpoint == payload.endpoint).first()
    if not subscription:
        subscription = WebPushSubscription(user_id=current_user.id, endpoint=payload.endpoint)
        db.add(subscription)
    subscription.user_id = current_user.id
    subscription.p256dh = payload.keys.p256dh
    subscription.auth = payload.keys.auth
    subscription.active = True
    db.commit()
    return {"ok": True}


@router.delete("/subscriptions", dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def delete_subscription(
    payload: PushSubscriptionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = (
        db.query(WebPushSubscription)
        .filter(WebPushSubscription.user_id == current_user.id, WebPushSubscription.endpoint == payload.endpoint)
        .first()
    )
    if subscription:
        subscription.active = False
        db.commit()
    return {"ok": True}
