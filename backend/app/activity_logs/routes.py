import csv
import io
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.database import get_db
from app.models import ActivityLog, Chatter, LoginAudit, Project, User
from app.rate_limit import sensitive_action_rate_limit_dependency
from app.roles.permissions import require_roles

router = APIRouter(prefix="/api/activity-logs", tags=["activity logs"])


@router.get("")
def list_activity_logs(
    q: str | None = None,
    type: str = Query("all"),
    status: str = Query("all"),
    user_id: int | None = None,
    project_id: int | None = None,
    chatter_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"admin"})
    return query_audit_logs(
        db,
        q=q,
        type_filter=type,
        status=status,
        user_id=user_id,
        project_id=project_id,
        chatter_id=chatter_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/export", dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def export_activity_logs(
    q: str | None = None,
    type: str = Query("all"),
    status: str = Query("all"),
    user_id: int | None = None,
    project_id: int | None = None,
    chatter_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"admin"})
    rows = query_audit_logs(
        db,
        q=q,
        type_filter=type,
        status=status,
        user_id=user_id,
        project_id=project_id,
        chatter_id=chatter_id,
        date_from=date_from,
        date_to=date_to,
        limit=5000,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "created_at", "type", "status", "description", "user", "project", "chatter"])
    for row in rows:
        writer.writerow([
            row.get("id"),
            row.get("created_at"),
            row.get("activity_type"),
            row.get("status"),
            row.get("description"),
            row.get("user_name") or row.get("login") or "",
            row.get("project_name") or "",
            row.get("chatter_name") or "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=anochat-audit-logs.csv"},
    )


def query_audit_logs(
    db: Session,
    *,
    q: str | None,
    type_filter: str,
    status: str,
    user_id: int | None,
    project_id: int | None,
    chatter_id: int | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
) -> list[dict]:
    rows: list[dict] = []
    include_activity = type_filter in {"", "all"} or type_matches_activity(type_filter)
    include_login = type_filter in {"", "all", "login"}
    start_at = datetime.combine(date_from, time.min) if date_from else None
    end_at = datetime.combine(date_to, time.max) if date_to else None

    if include_activity:
        query = db.query(ActivityLog)
        if status and status != "all":
            query = query.filter(ActivityLog.status == status)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if project_id:
            query = query.filter(ActivityLog.project_id == project_id)
        if chatter_id:
            query = query.filter(ActivityLog.chatter_id == chatter_id)
        if start_at:
            query = query.filter(ActivityLog.created_at >= start_at)
        if end_at:
            query = query.filter(ActivityLog.created_at <= end_at)
        if type_filter not in {"", "all", "activity"}:
            query = query.filter(ActivityLog.activity_type.ilike(f"%{type_filter}%"))
        if q:
            term = f"%{q.strip()}%"
            query = query.filter(or_(ActivityLog.activity_type.ilike(term), ActivityLog.description.ilike(term), ActivityLog.status.ilike(term)))
        activity_logs = query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
        rows.extend(format_activity_log(db, log) for log in activity_logs)

    if include_login and not project_id and not chatter_id:
        query = db.query(LoginAudit)
        if status and status != "all":
            query = query.filter(LoginAudit.status == status)
        if user_id:
            query = query.filter(LoginAudit.user_id == user_id)
        if start_at:
            query = query.filter(LoginAudit.created_at >= start_at)
        if end_at:
            query = query.filter(LoginAudit.created_at <= end_at)
        if q:
            term = f"%{q.strip()}%"
            query = query.filter(or_(LoginAudit.login.ilike(term), LoginAudit.status.ilike(term), LoginAudit.note.ilike(term)))
        login_logs = query.order_by(LoginAudit.created_at.desc()).limit(limit).all()
        rows.extend(format_login_log(db, log) for log in login_logs)

    return sorted(rows, key=lambda item: item["created_at"], reverse=True)[:limit]


def type_matches_activity(value: str) -> bool:
    return value in {"activity", "project", "chatter", "message", "user", "attachment"}


def format_activity_log(db: Session, log: ActivityLog) -> dict:
    user = db.get(User, log.user_id) if log.user_id else None
    project = db.get(Project, log.project_id) if log.project_id else None
    chatter = db.get(Chatter, log.chatter_id) if log.chatter_id else None
    return {
        "id": f"activity-{log.id}",
        "activity_type": log.activity_type,
        "description": log.description,
        "status": log.status,
        "project_id": log.project_id,
        "project_name": project.name if project else None,
        "chatter_id": log.chatter_id,
        "chatter_name": chatter.name if chatter else None,
        "user_id": log.user_id,
        "user_name": user.name if user else None,
        "created_at": log.created_at,
    }


def format_login_log(db: Session, log: LoginAudit) -> dict:
    user = db.get(User, log.user_id) if log.user_id else None
    return {
        "id": f"login-{log.id}",
        "activity_type": "login",
        "description": f"{log.login or 'Unknown user'} signed in" if log.status == "success" else f"{log.login or 'Unknown user'} failed to sign in",
        "status": log.status,
        "user_id": log.user_id,
        "user_name": user.name if user else None,
        "login": log.login,
        "created_at": log.created_at,
    }
