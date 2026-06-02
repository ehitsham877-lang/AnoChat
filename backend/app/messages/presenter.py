from app.models import Message, User
from app.roles.permissions import is_admin


def message_out(message: Message, current_user: User) -> dict:
    admin = is_admin(current_user)
    sender_admin = is_admin(message.sender)
    deleted_by = message.deleted_by
    body = (message.original_body or message.body) if (admin or sender_admin) else message.body
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
        "attachments": [] if message.is_deleted and not admin else message.attachments,
        "seen_by": message.seen_by,
        "created_at": message.created_at,
        "is_deleted": message.is_deleted,
        "deleted_by_id": message.deleted_by_id,
        "deleted_by_name": deleted_by.name if deleted_by else None,
        "deleted_at": message.deleted_at,
    }
