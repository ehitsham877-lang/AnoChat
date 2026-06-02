from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.activity_logs.service import log_activity
from app.auth.service import get_current_user
from app.common import get_or_404
from app.config import get_settings
from app.database import get_db
from app.models import Attachment, User
from app.schemas import AttachmentOut

router = APIRouter(prefix="/api/attachments", tags=["attachments"])
settings = get_settings()


@router.get("", response_model=list[AttachmentOut])
def list_attachments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.roles.permissions import is_admin

    query = db.query(Attachment).order_by(Attachment.created_at.desc())
    if not is_admin(current_user):
        query = query.filter(Attachment.uploaded_by_id == current_user.id)
    return query.limit(300).all()


@router.post("/upload", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    file: UploadFile = File(...),
    project_id: int | None = Form(default=None),
    chatter_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large")
    content_type = file.content_type or "application/octet-stream"
    if content_type not in settings.allowed_upload_type_set:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {content_type}")
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
        storage_path=str(path),
        uploaded_by_id=current_user.id,
        project_id=project_id,
        chatter_id=chatter_id,
    )
    db.add(attachment)
    log_activity(db, "attachment_uploaded", f"{current_user.name} uploaded {attachment.filename}.", current_user.id)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{attachment_id}")
def download_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attachment = get_or_404(db, Attachment, attachment_id)
    path = Path(attachment.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.filename)


@router.delete("/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attachment = get_or_404(db, Attachment, attachment_id)
    if attachment.uploaded_by_id != current_user.id:
        from app.roles.permissions import is_admin
        if not is_admin(current_user):
            raise HTTPException(status_code=403, detail="Only uploader or admin can delete attachments")
    path = Path(attachment.storage_path)
    if path.exists():
        path.unlink()
    log_activity(db, "attachment_deleted", f"{current_user.name} deleted attachment {attachment.filename}.", current_user.id)
    db.delete(attachment)
    db.commit()
    return {"ok": True}
