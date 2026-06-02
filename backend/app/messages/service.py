from sqlalchemy.orm import Session

from app.models import Attachment, Message
from app.messages.sanitize import sanitize_chatter_message
from app.schemas import MessageCreate


def create_message(db: Session, chatter_id: int, user_id: int, payload: MessageCreate) -> Message:
    message = Message(
        chatter_id=chatter_id,
        sender_id=user_id,
        body=sanitize_chatter_message(payload.body),
        original_body=payload.body,
        message_type=payload.message_type,
    )
    if payload.attachment_ids:
        message.attachments = db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).all()
    db.add(message)
    db.flush()
    return message
