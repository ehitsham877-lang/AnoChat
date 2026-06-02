from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Chatter, Message, Project, User


def counts(db: Session) -> dict[str, int]:
    return {
        "users": db.scalar(func.count(User.id)) or 0,
        "projects": db.scalar(func.count(Project.id)) or 0,
        "chatters": db.scalar(func.count(Chatter.id)) or 0,
        "messages": db.scalar(func.count(Message.id)) or 0,
    }
