from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from .db import get_db
from .models import Job, Recruiter, User, UserRole
from .schemas import JobCreate, JobRead, JobUpdate
from .auth_api import oauth2_scheme, decode_cognito_token

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# =====================================================
# HELPER – GET CURRENT RECRUITER
# =====================================================
def get_current_recruiter(
    db: Session,
    token: str,
) -> Recruiter:
    payload = decode_cognito_token(token)
    user = db.query(User).filter(User.cognito_sub == payload["sub"]).first()

    if not user or user.role != UserRole.recruiter:
        raise HTTPException(403, "Only recruiters allowed")

    recruiter = db.query(Recruiter).filter(
        Recruiter.user_id == user.id
    ).first()

    if not recruiter:
        raise HTTPException(404, "Recruiter profile not found")

    return recruiter


# =====================================================
# CREATE JOB (RECRUITER ONLY)
# =====================================================
@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    data: JobCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    recruiter = get_current_recruiter(db, token)

    job = Job(
        recruiter_id=recruiter.id,
        company_id=recruiter.company_id,
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


# =====================================================
# READ MY JOBS (RECRUITER ONLY)
# =====================================================
@router.get("/my")
def get_my_jobs(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    recruiter = get_current_recruiter(db, token)

    jobs = (
        db.query(Job)
        .filter(Job.recruiter_id == recruiter.id)
        .order_by(Job.created_at.desc())
        .all()
    )

    return [
        {
            "job_id": job.id,
            "title": job.title,
            "location": job.location,
            "is_active": job.is_active,
            "created_at": job.created_at,
        }
        for job in jobs
    ]


# =====================================================
# UNARCHIVE JOB
# =====================================================
@router.put("/{job_id}/unarchive")
def unarchive_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    recruiter = get_current_recruiter(db, token)

    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == recruiter.id,
    ).first()

    if not job:
        raise HTTPException(404, "Job not found")

    job.is_active = True
    db.commit()

    return {"message": "Job unarchived successfully"}


# =====================================================
# READ ALL JOBS (PUBLIC)
# =====================================================
@router.get("/", response_model=list[JobRead])
def get_all_jobs(db: Session = Depends(get_db)):
    return db.query(Job).filter(Job.is_active == True).all()


# =====================================================
# READ JOB BY ID (PUBLIC)
# =====================================================
@router.get("/{job_id}", response_model=JobRead)
def get_job_by_id(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.is_active == True
    ).first()

    if not job:
        raise HTTPException(404, "Job not found")

    return job


# =====================================================
# UPDATE JOB (RECRUITER ONLY)
# =====================================================
@router.put("/{job_id}", response_model=JobRead)
def update_job(
    job_id: UUID,
    data: JobUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    recruiter = get_current_recruiter(db, token)

    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == recruiter.id,
        Job.is_active == True
    ).first()

    if not job:
        raise HTTPException(404, "Job not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(job, key, value)

    db.commit()
    db.refresh(job)
    return job


# =====================================================
# DELETE JOB (SOFT DELETE)
# =====================================================
@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    recruiter = get_current_recruiter(db, token)

    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == recruiter.id,
        Job.is_active == True
    ).first()

    if not job:
        raise HTTPException(404, "Job not found")

    job.is_active = False
    db.commit()

