from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db import get_db
from app.models import Job, Recruiter
from app.schemas import JobCreate, JobRead

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    data: JobCreate,
    db: Session = Depends(get_db),
):
    # 1️⃣ Check recruiter exists
    recruiter = db.query(Recruiter).filter(
        Recruiter.id == data.recruiter_id
    ).first()

    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter not found")

    # 2️⃣ Create job
    job = Job(
        recruiter_id=data.recruiter_id,
        company_id=data.company_id,
        title=data.title,
        description=data.description,
        location=data.location,
        min_experience=data.min_experience,
        max_experience=data.max_experience,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        employment_type=data.employment_type,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job
