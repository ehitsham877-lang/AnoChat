from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.models import Message, User
from app.roles.permissions import is_admin


def utc_datetime(value):
    if not value:
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def message_edit_deadline(message: Message) -> datetime | None:
    created_at = utc_datetime(message.created_at)
    if not created_at:
        return None
    return created_at + timedelta(minutes=get_settings().message_edit_window_minutes)


def can_edit_message(message: Message, current_user: User) -> bool:
    if message.is_deleted or message.sender_id != current_user.id:
        return False
    deadline = message_edit_deadline(message)
    return bool(deadline and datetime.now(timezone.utc) <= deadline)


def message_out(message: Message, current_user: User) -> dict:
    admin = is_admin(current_user)
    sender_admin = is_admin(message.sender)
    deleted_by = message.deleted_by
    body = (message.original_body or message.body) if (admin or sender_admin) else message.body
    attachments = message.attachments if admin else [attachment for attachment in message.attachments if not attachment.is_deleted]
    own_message = message.sender_id == current_user.id
    can_edit = can_edit_message(message, current_user)
    edit_deadline = message_edit_deadline(message) if own_message and not message.is_deleted else None
    created_at = utc_datetime(message.created_at)
    updated_at = utc_datetime(message.updated_at)
    is_edited = bool(created_at and updated_at and updated_at > created_at and not message.is_deleted)
    if message.is_deleted and not admin:
        deleted_by_admin = bool(deleted_by and is_admin(deleted_by))
        body = "This message has been deleted by admin" if deleted_by_admin else "This message has been deleted"
    return {
        "id": message.id,
        "chatter_id": message.chatter_id,
        "sender_id": message.sender_id,
        "body": body,
        "message_type": message.message_type,
        "is_moderated": message.is_moderated,
        "moderation_reason": message.moderation_reason,
        "attachments": [] if message.is_deleted and not admin else attachments,
        "seen_by": message.seen_by if own_message else [],
        "created_at": message.created_at,
        "is_deleted": message.is_deleted,
        "deleted_by_id": message.deleted_by_id,
        "deleted_by_name": deleted_by.name if deleted_by else None,
        "deleted_at": message.deleted_at,
        "updated_at": message.updated_at,
        "can_edit": can_edit,
        "can_edit_until": edit_deadline,
        "is_edited": is_edited,
        **reply_preview(message, current_user),
    }


def reply_preview(message: Message, current_user: User) -> dict:
    replied = message.reply_to
    if not replied:
        return {
            "reply_to_id": None,
            "reply_to_sender_id": None,
            "reply_to_sender_name": None,
            "reply_to_body": None,
        }
    admin = is_admin(current_user)
    sender_admin = is_admin(replied.sender)
    body = (replied.original_body or replied.body) if (admin or sender_admin) else replied.body
    if replied.is_deleted and not admin:
        deleted_by_admin = bool(replied.deleted_by and is_admin(replied.deleted_by))
        body = "This message has been deleted by admin" if deleted_by_admin else "This message has been deleted"
    return {
        "reply_to_id": replied.id,
        "reply_to_sender_id": replied.sender_id,
        "reply_to_sender_name": replied.sender.name if replied.sender else None,
        "reply_to_body": body,
    }
