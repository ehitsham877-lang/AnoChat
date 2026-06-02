from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.activity_logs.service import log_activity
from app.common import get_or_404, set_chatter_members, set_project_members
from app.database import get_db
from app.models import ActivityLog, Attachment, Chatter, EmailLog, Project, User
from app.notifications.service import create_notification
from app.roles.permissions import assert_project_access, can_access_project, is_admin, require_roles
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return projects if is_admin(current_user) else [p for p in projects if can_access_project(current_user, p)]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    data = payload.model_dump()
    member_ids = data.pop("member_ids", [])
    project = Project(**data)
    db.add(project)
    db.flush()
    set_project_members(db, project, member_ids)
    chatter_member_ids = set(
        [current_user.id]
        + member_ids
        + ([project.manager_id] if project.manager_id else [])
        + ([project.customer_id] if project.customer_id else [])
    )
    chatter = Chatter(name=project.name, project_id=project.id, created_by_id=current_user.id)
    db.add(chatter)
    db.flush()
    set_chatter_members(db, chatter, list(chatter_member_ids))
    create_notification(db, current_user.id, "Project created", f"{project.name} is ready in your workspace.")
    create_notification(db, current_user.id, "Chatter created", f"{chatter.name} is ready for conversations.")
    log_activity(db, "project_created", f"{current_user.name} created project {project.name}.", current_user.id)
    log_activity(db, "chatter_created", f"{current_user.name} created chatter {chatter.name}.", current_user.id)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_or_404(db, Project, project_id)
    assert_project_access(current_user, project)
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_or_404(db, Project, project_id)
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can update projects")
    data = payload.model_dump(exclude_unset=True)
    member_ids = data.pop("member_ids", None)
    for key, value in data.items():
        setattr(project, key, value)
    if member_ids is not None:
        set_project_members(db, project, member_ids)
    log_activity(db, "project_updated", f"{current_user.name} updated project {project.name}.", current_user.id)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    project = get_or_404(db, Project, project_id)
    project_name = project.name
    project.members = []
    db.query(Chatter).filter(Chatter.project_id == project.id).update({"active": False}, synchronize_session=False)
    db.query(Attachment).filter(Attachment.project_id == project.id).update({"project_id": None}, synchronize_session=False)
    db.query(EmailLog).filter(EmailLog.project_id == project.id).update({"project_id": None}, synchronize_session=False)
    db.query(ActivityLog).filter(ActivityLog.project_id == project.id).update({"project_id": None}, synchronize_session=False)
    db.delete(project)
    log_activity(db, "project_deleted", f"{current_user.name} deleted project {project_name}.", current_user.id)
    db.commit()
    return {"ok": True}
