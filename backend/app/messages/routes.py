from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.activity_logs.service import log_activity
from app.auth.service import get_current_user
from app.common import get_or_404
from app.database import get_db
from app.models import Message, User
from app.messages.presenter import message_out
from app.messages.sanitize import sanitize_chatter_message
from app.roles.permissions import assert_chatter_access, is_admin
from app.schemas import MessageOut, MessageUpdate

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.put("/{message_id}", response_model=MessageOut)
def update_message(message_id: int, payload: MessageUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    message = get_or_404(db, Message, message_id)
    assert_chatter_access(current_user, message.chatter)
    if message.sender_id != current_user.id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only sender or admin can edit messages")
    data = payload.model_dump(exclude_unset=True)
    if "body" in data and data["body"] is not None:
        message.original_body = data["body"]
        data["body"] = data["body"] if is_admin(current_user) else sanitize_chatter_message(data["body"])
    for key, value in data.items():
        setattr(message, key, value)
    log_activity(db, "message_updated", f"{current_user.name} updated a message in {message.chatter.name}.", current_user.id)
    db.commit()
    db.refresh(message)
    return message_out(message, current_user)


@router.delete("/{message_id}", response_model=MessageOut)
def delete_message(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    message = get_or_404(db, Message, message_id)
    assert_chatter_access(current_user, message.chatter)
    if message.sender_id != current_user.id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only sender or admin can delete messages")
    chatter_name = message.chatter.name
    message.is_deleted = True
    message.deleted_by_id = current_user.id
    message.deleted_at = datetime.now(timezone.utc)
    log_activity(db, "message_deleted", f"{current_user.name} deleted a message in {chatter_name}.", current_user.id)
    db.commit()
    db.refresh(message)
    return message_out(message, current_user)


@router.post("/{message_id}/read")
def mark_read(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    message = get_or_404(db, Message, message_id)
    assert_chatter_access(current_user, message.chatter)
    if current_user not in message.seen_by:
        message.seen_by.append(current_user)
        db.commit()
    return {"ok": True}
