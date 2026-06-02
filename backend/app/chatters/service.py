from sqlalchemy.orm import Session

from app.common import set_chatter_members
from app.models import Chatter
from app.schemas import ChatterCreate


def create_chatter(db: Session, payload: ChatterCreate, user_id: int) -> Chatter:
    data = payload.model_dump()
    member_ids = data.pop("member_ids", [])
    if user_id not in member_ids:
        member_ids.append(user_id)
    chatter = Chatter(**data, created_by_id=user_id)
    db.add(chatter)
    db.flush()
    set_chatter_members(db, chatter, member_ids)
    return chatter
