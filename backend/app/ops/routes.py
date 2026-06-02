from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.database import get_db
from app.models import OpsDocument, OpsIncident, OpsKnowledgeArticle, OpsTask, User
from app.roles.permissions import require_roles

router = APIRouter(prefix="/api/operations", tags=["operations"])


@router.get("/tasks")
def tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    return db.query(OpsTask).order_by(OpsTask.created_at.desc()).limit(300).all()


@router.get("/documents")
def documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    return db.query(OpsDocument).filter(OpsDocument.active.is_(True)).order_by(OpsDocument.created_at.desc()).limit(300).all()


@router.get("/incidents")
def incidents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    return db.query(OpsIncident).order_by(OpsIncident.created_at.desc()).limit(300).all()


@router.get("/knowledge")
def knowledge(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_roles(current_user, {"admin"})
    return db.query(OpsKnowledgeArticle).filter(OpsKnowledgeArticle.state == "published").order_by(OpsKnowledgeArticle.updated_at.desc()).limit(300).all()
