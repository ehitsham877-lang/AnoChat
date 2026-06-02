from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.database import get_db
from app.models import Chatter, LoginAudit, Message, Project, User
from app.roles.permissions import require_roles

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "fastapi", "legacy_backend_dependency": False}


@router.get("/stats")
def stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    return {
        "users": db.scalar(func.count(User.id)),
        "projects": db.scalar(func.count(Project.id)),
        "chatters": db.scalar(func.count(Chatter.id)),
        "messages": db.scalar(func.count(Message.id)),
        "recent_logins": db.query(LoginAudit).order_by(LoginAudit.created_at.desc()).limit(20).all(),
    }
