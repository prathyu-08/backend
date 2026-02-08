from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from .db import get_db
from .models import Skill
from .schemas import SkillRead

router = APIRouter(prefix="/skills", tags=["Skills"])


@router.get("", response_model=list[SkillRead])
def search_skills(
    search: str = "",
    db: Session = Depends(get_db),
):
    """
    /skills?search=py
    """
    q = db.query(Skill)

    if search:
        q = q.filter(
            func.lower(Skill.name).like(f"%{search.lower()}%")
        )

    return q.order_by(Skill.name).limit(10).all()
