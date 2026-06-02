from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.database import get_db
from app.models import ActivityLog, LoginAudit, User
from app.roles.permissions import require_roles

router = APIRouter(prefix="/api/activity-logs", tags=["activity logs"])


@router.get("")
def list_activity_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    activity_logs = [
        {
            "id": f"activity-{log.id}",
            "activity_type": log.activity_type,
            "description": log.description,
            "status": log.status,
            "created_at": log.created_at,
        }
        for log in db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(500).all()
    ]
    login_logs = [
        {
            "id": f"login-{log.id}",
            "activity_type": "login",
            "description": f"{log.login or 'Unknown user'} signed in" if log.status == "success" else f"{log.login or 'Unknown user'} failed to sign in",
            "status": log.status,
            "created_at": log.created_at,
        }
        for log in db.query(LoginAudit).order_by(LoginAudit.created_at.desc()).limit(500).all()
    ]
    return sorted(activity_logs + login_logs, key=lambda item: item["created_at"], reverse=True)[:500]
