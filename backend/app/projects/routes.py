from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.activity_logs.service import log_activity
from app.common import get_or_404, project_access_ids, read_only_project_member_ids, revoke_user_sessions, set_chatter_members, set_project_members, sync_linked_chatters_from_project
from app.database import get_db
from app.models import ActivityLog, Attachment, Chatter, EmailLog, Project, User
from app.notifications.service import create_notification
from app.rate_limit import sensitive_action_rate_limit_dependency
from app.roles.permissions import assert_project_access, can_access_project, is_admin, require_project_write_access, require_roles, require_write_access
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    visible = projects if is_admin(current_user) else [p for p in projects if can_access_project(current_user, p)]
    return [project_out(db, project) for project in visible]


def project_out(db: Session, project: Project) -> Project:
    project.read_only_member_ids = read_only_project_member_ids(db, project.id)
    return project


@router.post("", response_model=ProjectOut, status_code=201, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    require_write_access(current_user)
    data = payload.model_dump()
    member_ids = data.pop("member_ids", [])
    read_only_member_ids = data.pop("read_only_member_ids", [])
    project = Project(**data)
    db.add(project)
    db.flush()
    set_project_members(db, project, member_ids, read_only_member_ids)
    chatter_member_ids = set(
        [current_user.id]
        + member_ids
        + ([project.manager_id] if project.manager_id else [])
        + ([project.customer_id] if project.customer_id else [])
    )
    chatter = Chatter(name=project.name, description=project.description, project_id=project.id, created_by_id=current_user.id)
    db.add(chatter)
    db.flush()
    set_chatter_members(db, chatter, list(chatter_member_ids), read_only_member_ids)
    create_notification(db, current_user.id, "Project created", f"{project.name} is ready in your workspace.")
    create_notification(db, current_user.id, "Chatter created", f"{chatter.name} is ready for conversations.")
    log_activity(db, "project_created", f"{current_user.name} created project {project.name}.", current_user.id, project_id=project.id)
    log_activity(db, "chatter_created", f"{current_user.name} created chatter {chatter.name}.", current_user.id, project_id=project.id, chatter_id=chatter.id)
    db.commit()
    db.refresh(project)
    return project_out(db, project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_or_404(db, Project, project_id)
    assert_project_access(current_user, project)
    return project_out(db, project)


@router.get("/{project_id}/activity")
def list_project_activity(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_or_404(db, Project, project_id)
    assert_project_access(current_user, project)
    chatter_ids = [row[0] for row in db.query(Chatter.id).filter(Chatter.project_id == project.id).all()]
    filters = [ActivityLog.project_id == project.id]
    if chatter_ids:
        filters.append(ActivityLog.chatter_id.in_(chatter_ids))
    rows = (
        db.query(ActivityLog)
        .filter(or_(*filters))
        .order_by(ActivityLog.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": log.id,
            "activity_type": log.activity_type,
            "description": log.description,
            "status": log.status,
            "project_id": log.project_id,
            "chatter_id": log.chatter_id,
            "user_id": log.user_id,
            "created_at": log.created_at,
        }
        for log in rows
    ]


@router.put("/{project_id}", response_model=ProjectOut, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_or_404(db, Project, project_id)
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can update projects")
    require_project_write_access(db, current_user, project)
    data = payload.model_dump(exclude_unset=True)
    member_ids = data.pop("member_ids", None)
    read_only_member_ids = data.pop("read_only_member_ids", None)
    previous_access_ids = project_access_ids(project)
    sync_membership = member_ids is not None or read_only_member_ids is not None or "manager_id" in data or "customer_id" in data
    for key, value in data.items():
        setattr(project, key, value)
    if sync_membership:
        next_member_ids = member_ids if member_ids is not None else [member.id for member in project.members]
        next_read_only_member_ids = read_only_member_ids if read_only_member_ids is not None else read_only_project_member_ids(db, project.id)
        set_project_members(
            db,
            project,
            next_member_ids,
            next_read_only_member_ids,
        )
        db.flush()
        db.refresh(project)
        removed_from_chatters = sync_linked_chatters_from_project(db, project, next_member_ids, next_read_only_member_ids)
        current_access_ids = project_access_ids(project)
        revoked_user_ids = (previous_access_ids | removed_from_chatters) - current_access_ids - {current_user.id}
        revoke_user_sessions(db, revoked_user_ids)
    log_activity(db, "project_updated", f"{current_user.name} updated project {project.name}.", current_user.id, project_id=project.id)
    db.commit()
    db.refresh(project)
    return project_out(db, project)


@router.delete("/{project_id}", dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    project = get_or_404(db, Project, project_id)
    require_project_write_access(db, current_user, project)
    project_name = project.name
    project.members = []
    db.query(Chatter).filter(Chatter.project_id == project.id).update({"active": False}, synchronize_session=False)
    db.query(Attachment).filter(Attachment.project_id == project.id).update({"project_id": None}, synchronize_session=False)
    db.query(EmailLog).filter(EmailLog.project_id == project.id).update({"project_id": None}, synchronize_session=False)
    db.query(ActivityLog).filter(ActivityLog.project_id == project.id).update({"project_id": None}, synchronize_session=False)
    db.delete(project)
    log_activity(db, "project_deleted", f"{current_user.name} deleted project {project_name}.", current_user.id, project_id=project.id)
    db.commit()
    return {"ok": True}
