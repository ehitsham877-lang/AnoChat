from sqlalchemy.orm import Session

from app.models import EmailLog
from app.schemas import InboundEmail


def record_inbound_email(db: Session, payload: InboundEmail) -> EmailLog:
    log = EmailLog(
        email_from=payload.email_from,
        email_to=payload.email_to,
        subject=payload.subject,
        body_excerpt=(payload.body or "")[:2000],
        project_id=payload.project_id,
        chatter_id=payload.chatter_id,
        attachment_count=payload.attachment_count,
    )
    db.add(log)
    db.flush()
    return log
