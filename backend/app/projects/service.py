from sqlalchemy.orm import Session

from app.common import set_project_members
from app.models import Project
from app.schemas import ProjectCreate


def create_project(db: Session, payload: ProjectCreate) -> Project:
    data = payload.model_dump()
    member_ids = data.pop("member_ids", [])
    project = Project(**data)
    db.add(project)
    db.flush()
    set_project_members(db, project, member_ids)
    return project
