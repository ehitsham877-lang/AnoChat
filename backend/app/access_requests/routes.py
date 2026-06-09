from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.activity_logs.service import log_activity
from app.auth.service import get_current_user
from app.common import get_or_404, read_only_chatter_member_ids, read_only_project_member_ids, set_chatter_members, set_project_members
from app.database import get_db
from app.models import AccessRequest, Chatter, Project, Role, User
from app.notifications.service import notify_users
from app.rate_limit import access_request_rate_limit_dependency, sensitive_action_rate_limit_dependency
from app.roles.permissions import can_access_chatter, can_access_project, is_admin, require_roles, require_write_access
from app.schemas import AccessRequestCreate, AccessRequestOption, AccessRequestOptionsOut, AccessRequestOut

router = APIRouter(prefix="/api/access-requests", tags=["access requests"])

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
RESOURCE_PROJECT = "project"
RESOURCE_CHATTER = "chatter"


def access_request_out(item: AccessRequest) -> AccessRequestOut:
    resource = item.project if item.resource_type == RESOURCE_PROJECT else item.chatter
    return AccessRequestOut(
        id=item.id,
        requester_id=item.requester_id,
        requester_name=item.requester.name if item.requester else "Unknown user",
        requester_email=item.requester.email if item.requester else None,
        resource_type=item.resource_type,
        resource_id=item.project_id if item.resource_type == RESOURCE_PROJECT else item.chatter_id,
        resource_name=resource.name if resource else "Deleted resource",
        project_id=item.project_id,
        chatter_id=item.chatter_id,
        message=item.message,
        status=item.status,
        processed_by_id=item.processed_by_id,
        processed_by_name=item.processed_by.name if item.processed_by else None,
        processed_at=item.processed_at,
        created_at=item.created_at,
    )


def admin_ids(db: Session) -> list[int]:
    return [
        row[0]
        for row in (
            db.query(User.id)
            .join(User.roles)
            .filter(Role.name == "admin", User.active.is_(True))
            .all()
        )
    ]


@router.get("", response_model=list[AccessRequestOut])
def list_access_requests(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AccessRequest).order_by(AccessRequest.created_at.desc())
    if status:
        query = query.filter(AccessRequest.status == status)
    if not is_admin(current_user):
        query = query.filter(AccessRequest.requester_id == current_user.id)
    return [access_request_out(item) for item in query.all()]


@router.get("/options", response_model=AccessRequestOptionsOut)
def access_request_options(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = db.query(Project).order_by(Project.name.asc()).all()
    chatters = db.query(Chatter).filter(Chatter.active.is_(True)).order_by(Chatter.name.asc()).all()
    if not is_admin(current_user):
        projects = [project for project in projects if not can_access_project(current_user, project)]
        chatters = [chatter for chatter in chatters if not can_access_chatter(current_user, chatter)]
    return AccessRequestOptionsOut(
        projects=[AccessRequestOption(id=project.id, name=project.name) for project in projects],
        chatters=[AccessRequestOption(id=chatter.id, name=chatter.name) for chatter in chatters],
    )


@router.post("", response_model=AccessRequestOut, status_code=201, dependencies=[Depends(access_request_rate_limit_dependency)])
def create_access_request(
    payload: AccessRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource_type = payload.resource_type.strip().lower()
    if resource_type not in {RESOURCE_PROJECT, RESOURCE_CHATTER}:
        raise HTTPException(status_code=400, detail="Choose project or chatter access")
    if is_admin(current_user):
        raise HTTPException(status_code=409, detail="Admins already have access")

    project_id = None
    chatter_id = None
    resource_name = ""
    if resource_type == RESOURCE_PROJECT:
        if not payload.project_id:
            raise HTTPException(status_code=400, detail="Choose a project")
        project = get_or_404(db, Project, payload.project_id)
        if can_access_project(current_user, project):
            raise HTTPException(status_code=409, detail="You already have access to this project")
        project_id = project.id
        resource_name = project.name
    else:
        if not payload.chatter_id:
            raise HTTPException(status_code=400, detail="Choose a chatter")
        chatter = get_or_404(db, Chatter, payload.chatter_id)
        if not chatter.active:
            raise HTTPException(status_code=404, detail="Chatter not found")
        if can_access_chatter(current_user, chatter):
            raise HTTPException(status_code=409, detail="You already have access to this chatter")
        chatter_id = chatter.id
        resource_name = chatter.name

    duplicate = db.query(AccessRequest).filter(
        AccessRequest.requester_id == current_user.id,
        AccessRequest.resource_type == resource_type,
        AccessRequest.project_id == project_id,
        AccessRequest.chatter_id == chatter_id,
        AccessRequest.status == PENDING,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A pending request already exists")

    request = AccessRequest(
        requester_id=current_user.id,
        resource_type=resource_type,
        project_id=project_id,
        chatter_id=chatter_id,
        message=(payload.message or "").strip() or None,
        status=PENDING,
    )
    db.add(request)
    db.flush()
    notify_users(
        db,
        [user_id for user_id in admin_ids(db) if user_id != current_user.id],
        "Access request pending",
        f"{current_user.name} requested access to {resource_name}.",
    )
    log_activity(db, "access_requested", f"{current_user.name} requested access to {resource_name}.", current_user.id, project_id=project_id, chatter_id=chatter_id)
    db.commit()
    db.refresh(request)
    return access_request_out(request)


@router.post("/{request_id}/approve", response_model=AccessRequestOut, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def approve_access_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    require_write_access(current_user)
    request = get_or_404(db, AccessRequest, request_id)
    if request.status != PENDING:
        raise HTTPException(status_code=409, detail="This request has already been processed")

    if request.resource_type == RESOURCE_PROJECT:
        project = get_or_404(db, Project, request.project_id)
        member_ids = [member.id for member in project.members]
        if request.requester_id not in member_ids:
            member_ids.append(request.requester_id)
        set_project_members(db, project, member_ids, read_only_project_member_ids(db, project.id))
        for chatter in db.query(Chatter).filter(Chatter.project_id == project.id, Chatter.active.is_(True)).all():
            chatter_member_ids = [member.id for member in chatter.members]
            if request.requester_id not in chatter_member_ids:
                chatter_member_ids.append(request.requester_id)
                set_chatter_members(db, chatter, chatter_member_ids, read_only_chatter_member_ids(db, chatter.id))
        resource_name = project.name
    else:
        chatter = get_or_404(db, Chatter, request.chatter_id)
        member_ids = [member.id for member in chatter.members]
        if request.requester_id not in member_ids:
            member_ids.append(request.requester_id)
        set_chatter_members(db, chatter, member_ids, read_only_chatter_member_ids(db, chatter.id))
        resource_name = chatter.name

    request.status = APPROVED
    request.processed_by_id = current_user.id
    request.processed_at = datetime.now(timezone.utc)
    notify_users(db, [request.requester_id], "Access approved", f"You can now access {resource_name}.")
    log_activity(db, "access_approved", f"{current_user.name} approved access to {resource_name} for {request.requester.name}.", current_user.id, project_id=request.project_id, chatter_id=request.chatter_id)
    db.commit()
    db.refresh(request)
    return access_request_out(request)


@router.post("/{request_id}/reject", response_model=AccessRequestOut, dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def reject_access_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    require_write_access(current_user)
    request = get_or_404(db, AccessRequest, request_id)
    if request.status != PENDING:
        raise HTTPException(status_code=409, detail="This request has already been processed")
    resource = request.project if request.resource_type == RESOURCE_PROJECT else request.chatter
    resource_name = resource.name if resource else "this resource"
    request.status = REJECTED
    request.processed_by_id = current_user.id
    request.processed_at = datetime.now(timezone.utc)
    notify_users(db, [request.requester_id], "Access request declined", f"Your request for {resource_name} was declined.")
    log_activity(db, "access_rejected", f"{current_user.name} rejected access to {resource_name} for {request.requester.name}.", current_user.id, project_id=request.project_id, chatter_id=request.chatter_id)
    db.commit()
    db.refresh(request)
    return access_request_out(request)
