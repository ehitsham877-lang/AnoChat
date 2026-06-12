from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.activity_logs.service import log_activity
from app.auth.service import get_current_user
from app.common import get_or_404
from app.config import get_settings
from app.database import get_db
from app.models import Attachment, Chatter, Project, User
from app.rate_limit import sensitive_action_rate_limit_dependency, upload_rate_limit_dependency
from app.roles.permissions import assert_chatter_access, assert_project_access, is_admin, require_chatter_write_access, require_project_write_access, require_write_access
from app.schemas import AttachmentOut

router = APIRouter(prefix="/api/attachments", tags=["attachments"])
settings = get_settings()

EXTRA_ALLOWED_CONTENT_TYPES = {
    "application/json": "application/json",
    "text/json": "application/json",
    "application/zip": "application/zip",
    "application/x-zip-compressed": "application/zip",
    "application/x-zip": "application/zip",
    "multipart/x-zip": "application/zip",
    "application/x-compressed": "application/zip",
    "application/zip-compressed": "application/zip",
}

EXTENSION_CONTENT_TYPES = {
    ".json": {"application/json", "text/json", "text/plain", "application/octet-stream"},
    ".zip": {
        "application/zip",
        "application/x-zip-compressed",
        "application/x-zip",
        "multipart/x-zip",
        "application/x-compressed",
        "application/zip-compressed",
        "application/octet-stream",
    },
}


def allowed_content_type(filename: str | None, content_type: str) -> str | None:
    content_type = (content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    suffix = Path(filename or "").suffix.lower()
    extension_types = EXTENSION_CONTENT_TYPES.get(suffix)
    if extension_types and content_type in extension_types:
        return "application/json" if suffix == ".json" else "application/zip"
    if content_type in EXTRA_ALLOWED_CONTENT_TYPES:
        return EXTRA_ALLOWED_CONTENT_TYPES[content_type]
    if content_type in settings.allowed_upload_type_set:
        return content_type
    return None


@router.get("", response_model=list[AttachmentOut])
def list_attachments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Attachment).order_by(Attachment.created_at.desc()).filter(Attachment.is_deleted.is_(False))
    if not is_admin(current_user):
        # Non-admin users can see all attachments in projects/chatters they have access to
        accessible_project_ids = set()
        accessible_chatter_ids = set()
        
        # Get all projects this user has access to
        user_projects = db.query(Project).filter(
            (Project.manager_id == current_user.id) |
            (Project.customer_id == current_user.id) |
            (Project.members.any(User.id == current_user.id))
        ).all()
        accessible_project_ids = {p.id for p in user_projects}
        
        # Get all chatters this user has access to
        user_chatters = db.query(Chatter).filter(
            (Chatter.created_by_id == current_user.id) |
            (Chatter.members.any(User.id == current_user.id))
        ).all()
        accessible_chatter_ids = {c.id for c in user_chatters}
        
        # Build conditions for accessible attachments
        conditions = []
        if accessible_project_ids:
            conditions.append(Attachment.project_id.in_(accessible_project_ids))
        if accessible_chatter_ids:
            conditions.append(Attachment.chatter_id.in_(accessible_chatter_ids))
        
        # Apply conditions - if user has no access to any projects/chatters, return empty
        if conditions:
            query = query.filter(or_(*conditions))
        else:
            query = query.filter(Attachment.id == -1)
    return query.limit(300).all()


@router.post("/upload", response_model=AttachmentOut, status_code=201, dependencies=[Depends(upload_rate_limit_dependency)])
async def upload_attachment(
    file: UploadFile = File(...),
    project_id: int | None = Form(default=None),
    chatter_id: int | None = Form(default=None),
    duration_seconds: float | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_write_access(current_user)
    if chatter_id:
        chatter = get_or_404(db, Chatter, chatter_id)
        assert_chatter_access(current_user, chatter)
        require_chatter_write_access(db, current_user, chatter)
    if project_id:
        project = get_or_404(db, Project, project_id)
        assert_project_access(current_user, project)
        require_project_write_access(db, current_user, project)
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large")
    raw_content_type = file.content_type or "application/octet-stream"
    content_type = allowed_content_type(file.filename, raw_content_type)
    if not content_type:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {raw_content_type}")
    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid4().hex}_{Path(file.filename or 'upload.bin').name}"
    path = upload_root / stored
    path.write_bytes(content)
    attachment = Attachment(
        filename=file.filename or stored,
        stored_filename=stored,
        content_type=content_type,
        size_bytes=len(content),
        duration_seconds=duration_seconds if content_type.startswith("audio/") else None,
        storage_path=str(path),
        uploaded_by_id=current_user.id,
        project_id=project_id,
        chatter_id=chatter_id,
    )
    db.add(attachment)
    log_activity(db, "attachment_uploaded", f"{current_user.name} uploaded {attachment.filename}.", current_user.id, project_id=project_id, chatter_id=chatter_id)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{attachment_id}")
def download_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attachment = get_or_404(db, Attachment, attachment_id)
    if attachment.is_deleted and not is_admin(current_user):
        raise HTTPException(status_code=404, detail="Attachment deleted")
    path = Path(attachment.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.filename)


@router.delete("/{attachment_id}", dependencies=[Depends(sensitive_action_rate_limit_dependency)])
def delete_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attachment = get_or_404(db, Attachment, attachment_id)
    require_write_access(current_user)
    if attachment.chatter_id:
        chatter = get_or_404(db, Chatter, attachment.chatter_id)
        require_chatter_write_access(db, current_user, chatter)
    if attachment.project_id:
        project = get_or_404(db, Project, attachment.project_id)
        require_project_write_access(db, current_user, project)
    if attachment.uploaded_by_id != current_user.id:
        if not is_admin(current_user):
            raise HTTPException(status_code=403, detail="Only uploader or admin can delete attachments")
    attachment.is_deleted = True
    attachment.deleted_by_id = current_user.id
    attachment.deleted_at = func.now()
    log_activity(db, "attachment_deleted", f"{current_user.name} deleted attachment {attachment.filename}.", current_user.id, project_id=attachment.project_id, chatter_id=attachment.chatter_id)
    db.commit()
    return {"ok": True}
