from sqlalchemy.orm import Session

from app.models import ActivityLog


def log_activity(
    db: Session,
    activity_type: str,
    description: str,
    user_id: int | None = None,
    status: str = "success",
    project_id: int | None = None,
    chatter_id: int | None = None,
) -> ActivityLog:
    log = ActivityLog(
        activity_type=activity_type,
        description=description,
        user_id=user_id,
        status=status,
        project_id=project_id,
        chatter_id=chatter_id,
    )
    db.add(log)
    db.flush()
    return log
