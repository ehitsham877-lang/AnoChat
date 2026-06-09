from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.activity_logs.service import log_activity
from app.auth.service import get_current_user
from app.common import get_or_404, read_only_chatter_member_ids, set_chatter_members
from app.database import get_db
from app.models import Chatter, Message, TypingState, User
from app.messages.presenter import message_out
from app.messages.sanitize import sanitize_chatter_message
from app.notifications.service import PUSH_CHATTER_MESSAGE, create_notification, notify_users
from app.rate_limit import message_rate_limit_dependency, sensitive_action_rate_limit_dependency, typing_rate_limit_dependency
from app.roles.permissions import assert_chatter_access, can_access_chatter, is_admin, require_chatter_write_access, require_roles, require_write_access
from app.schemas import ChatterCreate, ChatterOut, ChatterUpdate, MessageCreate, MessageOut, TypingStateUpdate, TypingUserOut

router = APIRouter(prefix="/api/chatters", tags=["chatters"])
TYPING_TTL_SECONDS = 6


def unread_count_for(chatter: Chatter, current_user: User) -> int:
    return sum(
        1
        for message in chatter.messages
        if message.sender_id != current_user.id
        and not message.is_deleted
        and current_user not in message.seen_by
    )


def chatter_out(chatter: Chatter, current_user: User) -> Chatter:
    chatter.unread_count = unread_count_for(chatter, current_user)
    return chatter


def chatter_with_read_only(db: Session, chatter: Chatter, current_user: User) -> Chatter:
    chatter.read_only_member_ids = read_only_chatter_member_ids(db, chatter.id)
    return chatter_out(chatter, current_user)


@router.get("", response_model=list[ChatterOut])
def list_chatters(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chatters = db.query(Chatter).filter(Chatter.active.is_(True)).order_by(Chatter.last_activity.desc()).all()
    visible = chatters if is_admin(current_user) else [c for c in chatters if can_access_chatter(current_user, c)]
    return [chatter_with_read_only(db, chatter, current_user) for chatter in visible]


@router.post("", response_model=ChatterOut, status_code=201, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def create_chatter(payload: ChatterCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    require_write_access(current_user)
    data = payload.model_dump()
    member_ids = data.pop("member_ids", [])
    read_only_member_ids = data.pop("read_only_member_ids", [])
    if current_user.id not in member_ids:
        member_ids.append(current_user.id)
    chatter = Chatter(**data, created_by_id=current_user.id)
    db.add(chatter)
    db.flush()
    set_chatter_members(db, chatter, member_ids, read_only_member_ids)
    create_notification(db, current_user.id, "Chatter created", f"{chatter.name} is ready for conversations.")
    log_activity(db, "chatter_created", f"{current_user.name} created chatter {chatter.name}.", current_user.id, project_id=chatter.project_id, chatter_id=chatter.id)
    db.commit()
    db.refresh(chatter)
    return chatter_with_read_only(db, chatter, current_user)


@router.get("/{chatter_id}", response_model=ChatterOut)
def get_chatter(chatter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chatter = get_or_404(db, Chatter, chatter_id)
    assert_chatter_access(current_user, chatter)
    return chatter_with_read_only(db, chatter, current_user)


@router.put("/{chatter_id}", response_model=ChatterOut, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def update_chatter(chatter_id: int, payload: ChatterUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chatter = get_or_404(db, Chatter, chatter_id)
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can update chatters")
    require_chatter_write_access(db, current_user, chatter)
    data = payload.model_dump(exclude_unset=True)
    member_ids = data.pop("member_ids", None)
    read_only_member_ids = data.pop("read_only_member_ids", None)
    for key, value in data.items():
        setattr(chatter, key, value)
    if member_ids is not None or read_only_member_ids is not None:
        set_chatter_members(
            db,
            chatter,
            member_ids if member_ids is not None else [member.id for member in chatter.members],
            read_only_member_ids if read_only_member_ids is not None else read_only_chatter_member_ids(db, chatter.id),
        )
    log_activity(db, "chatter_updated", f"{current_user.name} updated chatter {chatter.name}.", current_user.id, project_id=chatter.project_id, chatter_id=chatter.id)
    db.commit()
    db.refresh(chatter)
    return chatter_with_read_only(db, chatter, current_user)


@router.delete("/{chatter_id}", dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def delete_chatter(chatter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chatter = get_or_404(db, Chatter, chatter_id)
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can delete chatters")
    require_chatter_write_access(db, current_user, chatter)
    chatter.active = False
    log_activity(db, "chatter_deleted", f"{current_user.name} deleted chatter {chatter.name}.", current_user.id, project_id=chatter.project_id, chatter_id=chatter.id)
    db.commit()
    return {"ok": True}


@router.get("/{chatter_id}/messages", response_model=list[MessageOut])
def list_messages(chatter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chatter = get_or_404(db, Chatter, chatter_id)
    assert_chatter_access(current_user, chatter)
    query = db.query(Message).filter(Message.chatter_id == chatter_id)
    messages = query.order_by(Message.created_at.asc()).limit(500).all()
    changed = False
    for message in messages:
        if message.sender_id != current_user.id and current_user not in message.seen_by:
            message.seen_by.append(current_user)
            changed = True
    if changed:
        db.commit()
    return [message_out(message, current_user) for message in messages]


@router.get("/{chatter_id}/typing", response_model=list[TypingUserOut])
def list_typing(chatter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chatter = get_or_404(db, Chatter, chatter_id)
    assert_chatter_access(current_user, chatter)
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=TYPING_TTL_SECONDS)
    rows = (
        db.query(TypingState, User)
        .join(User, User.id == TypingState.user_id)
        .filter(
            TypingState.chatter_id == chatter_id,
            TypingState.user_id != current_user.id,
            TypingState.updated_at >= cutoff,
        )
        .order_by(TypingState.updated_at.desc())
        .limit(5)
        .all()
    )
    return [TypingUserOut(id=user.id, name=user.name or user.login or user.email) for _, user in rows]


@router.post("/{chatter_id}/typing", dependencies=[Depends(typing_rate_limit_dependency)])
def update_typing(chatter_id: int, payload: TypingStateUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chatter = get_or_404(db, Chatter, chatter_id)
    assert_chatter_access(current_user, chatter)
    require_chatter_write_access(db, current_user, chatter)
    if not payload.is_typing:
        db.execute(delete(TypingState).where(TypingState.chatter_id == chatter_id, TypingState.user_id == current_user.id))
        db.commit()
        return {"ok": True}
    state = db.query(TypingState).filter(TypingState.chatter_id == chatter_id, TypingState.user_id == current_user.id).first()
    if not state:
        state = TypingState(chatter_id=chatter_id, user_id=current_user.id)
        db.add(state)
    state.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/{chatter_id}/messages", response_model=MessageOut, status_code=201, dependencies=[Depends(message_rate_limit_dependency)])
def create_message(chatter_id: int, payload: MessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models import Attachment

    chatter = get_or_404(db, Chatter, chatter_id)
    assert_chatter_access(current_user, chatter)
    require_chatter_write_access(db, current_user, chatter)
    sanitized_body = payload.body if is_admin(current_user) else sanitize_chatter_message(payload.body)
    reply_to_id = None
    if payload.reply_to_id:
        replied = get_or_404(db, Message, payload.reply_to_id)
        if replied.chatter_id != chatter_id:
            raise HTTPException(status_code=400, detail="Reply message belongs to another chatter")
        reply_to_id = replied.id
    message = Message(chatter_id=chatter_id, sender_id=current_user.id, body=sanitized_body, original_body=payload.body, message_type=payload.message_type, reply_to_id=reply_to_id)
    if payload.attachment_ids:
        message.attachments = db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).all()
    chatter.last_message_preview = sanitized_body[:512]
    chatter.last_message_author_id = current_user.id
    db.add(message)
    db.execute(delete(TypingState).where(TypingState.chatter_id == chatter_id, TypingState.user_id == current_user.id))
    notify_users(
        db,
        [member.id for member in chatter.members if member.id != current_user.id],
        f"New message in {chatter.name}",
        sanitized_body[:140],
        push_category=PUSH_CHATTER_MESSAGE,
        action_url="/frontend/index.html",
    )
    log_activity(db, "message_sent", f"{current_user.name} sent a message in {chatter.name}.", current_user.id, project_id=chatter.project_id, chatter_id=chatter.id)
    db.commit()
    db.refresh(message)
    return message_out(message, current_user)
