from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activity_logs.service import log_activity
from app.auth.password import hash_password
from app.auth.service import get_current_user
from app.common import ensure_roles, get_or_404
from app.database import get_db
from app.models import (
    ActivityLog,
    Attachment,
    AttendanceLog,
    CallSignal,
    Chatter,
    EmailLog,
    LoginAudit,
    Message,
    Notification,
    NotificationPreference,
    Project,
    SignupRequest,
    TypingState,
    User,
    WebPushSubscription,
    message_attachments,
    message_seen,
)
from app.notifications.service import create_notification
from app.rate_limit import sensitive_action_rate_limit_dependency
from app.roles.permissions import KNOWN_ROLES, is_admin, require_roles, require_write_access
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if is_admin(current_user):
        return db.query(User).order_by(User.name).all()
    return [current_user]


@router.post("", response_model=UserOut, status_code=201, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def create_user(payload: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    require_write_access(current_user)
    email = str(payload.email).strip().lower()
    login = str(payload.login or email).strip().lower()
    if db.query(User).filter((User.login == login) | (User.email == email)).first():
        raise HTTPException(status_code=409, detail=f"User already exists for {email}")
    role_names = [role for role in (payload.roles or ["customer"]) if role in KNOWN_ROLES]
    if not role_names:
        raise HTTPException(status_code=400, detail="Select a valid role")
    user = User(
        name=payload.name,
        login=login,
        email=email,
        phone=payload.phone,
        active=payload.active,
        read_only=payload.read_only,
        hashed_password=hash_password(payload.password),
        roles=ensure_roles(db, role_names),
    )
    db.add(user)
    create_notification(db, current_user.id, "User created", f"{user.name} was added with {', '.join(role_names)} access.")
    log_activity(db, "user_created", f"{current_user.name} created user {user.name}.", current_user.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"User already exists for {email}") from None
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return get_or_404(db, User, user_id)


@router.put("/{user_id}", response_model=UserOut, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    user = get_or_404(db, User, user_id)
    data = payload.model_dump(exclude_unset=True)
    roles = data.pop("roles", None)
    password = data.pop("password", None)
    if roles is not None or "active" in data or "read_only" in data:
        require_roles(current_user, {"admin"})
        require_write_access(current_user)
    elif current_user.id != user_id:
        require_write_access(current_user)
    if "messenger_status" in data and data["messenger_status"] not in {"online", "away", "busy", "offline"}:
        raise HTTPException(status_code=400, detail="Select a valid presence status")
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"]).strip().lower()
    if "login" in data and data["login"] is not None:
        data["login"] = str(data["login"]).strip().lower()
    was_active = user.active
    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.hashed_password = hash_password(password)
    if roles is not None:
        require_roles(current_user, {"admin"})
        user.roles = ensure_roles(db, roles)
    if "active" in data and was_active and not user.active:
        log_activity(db, "user_deactivated", f"{current_user.name} deactivated user {user.name}.", current_user.id)
    elif "active" in data and not was_active and user.active:
        log_activity(db, "user_activated", f"{current_user.name} activated user {user.name}.", current_user.id)
    else:
        log_activity(db, "user_updated", f"{current_user.name} updated user {user.name}.", current_user.id)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    require_write_access(current_user)
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    user = get_or_404(db, User, user_id)
    user_name = user.name
    sent_message_ids = [row[0] for row in db.query(Message.id).filter(Message.sender_id == user.id).all()]
    if sent_message_ids:
        db.execute(message_attachments.delete().where(message_attachments.c.message_id.in_(sent_message_ids)))
        db.execute(message_seen.delete().where(message_seen.c.message_id.in_(sent_message_ids)))
        db.query(Message).filter(Message.id.in_(sent_message_ids)).delete(synchronize_session=False)
    user.roles = []
    user.projects = []
    user.chatters = []
    db.query(Project).filter(Project.manager_id == user.id).update({"manager_id": None}, synchronize_session=False)
    db.query(Project).filter(Project.customer_id == user.id).update({"customer_id": None}, synchronize_session=False)
    db.query(Chatter).filter(Chatter.created_by_id == user.id).update({"created_by_id": None}, synchronize_session=False)
    db.query(Chatter).filter(Chatter.last_message_author_id == user.id).update({"last_message_author_id": None}, synchronize_session=False)
    db.query(Attachment).filter(Attachment.uploaded_by_id == user.id).update({"uploaded_by_id": None}, synchronize_session=False)
    db.query(ActivityLog).filter(ActivityLog.user_id == user.id).update({"user_id": None}, synchronize_session=False)
    db.query(EmailLog).filter(EmailLog.user_id == user.id).update({"user_id": None}, synchronize_session=False)
    db.query(LoginAudit).filter(LoginAudit.user_id == user.id).update({"user_id": None}, synchronize_session=False)
    db.query(SignupRequest).filter(SignupRequest.user_id == user.id).update({"user_id": None}, synchronize_session=False)
    db.query(SignupRequest).filter(SignupRequest.processed_by_id == user.id).update({"processed_by_id": None}, synchronize_session=False)
    db.query(AttendanceLog).filter(AttendanceLog.user_id == user.id).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.user_id == user.id).delete(synchronize_session=False)
    db.query(NotificationPreference).filter(NotificationPreference.user_id == user.id).delete(synchronize_session=False)
    db.query(WebPushSubscription).filter(WebPushSubscription.user_id == user.id).delete(synchronize_session=False)
    db.query(TypingState).filter(TypingState.user_id == user.id).delete(synchronize_session=False)
    db.query(CallSignal).filter(CallSignal.sender_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    log_activity(db, "user_deleted", f"{current_user.name} deleted user {user_name}.", current_user.id)
    db.commit()
    return {"ok": True}


@router.put("/{user_id}/role", response_model=UserOut, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def set_role(user_id: int, roles: list[str], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    require_write_access(current_user)
    user = get_or_404(db, User, user_id)
    user.roles = ensure_roles(db, roles)
    log_activity(db, "role_updated", f"{current_user.name} updated roles for {user.name}.", current_user.id)
    db.commit()
    db.refresh(user)
    return user
