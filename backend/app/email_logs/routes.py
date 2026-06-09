from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.database import get_db
from app.models import EmailLog, User
from app.rate_limit import public_write_rate_limit_dependency
from app.roles.permissions import require_roles
from app.schemas import InboundEmail

router = APIRouter(tags=["email"])


@router.get("/api/email-logs")
def list_email_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    return db.query(EmailLog).order_by(EmailLog.created_at.desc()).limit(500).all()


@router.post("/api/email/inbound", status_code=201, dependencies=[Depends(public_write_rate_limit_dependency)])
def inbound_email(payload: InboundEmail, db: Session = Depends(get_db)):
    log = EmailLog(
        email_from=payload.email_from,
        email_to=payload.email_to,
        subject=payload.subject,
        body_excerpt=(payload.body or "")[:2000],
        project_id=payload.project_id,
        chatter_id=payload.chatter_id,
        attachment_count=payload.attachment_count,
        status="received",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"ok": True, "id": log.id}
