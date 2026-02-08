from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from .db import get_db
from .models import Job, Recruiter
from .auth_api import get_current_recruiter
from .models import JobShare
from .email_utils import send_email
from .email_templates import job_shared

router = APIRouter(prefix="/job-shares", tags=["Job Sharing"])


# SHARE JOB WITH OTHER RECRUITERS + EMAIL NOTIFICATION
@router.post("/{job_id}/share")
def share_job(
    job_id: UUID,
    recruiter_ids: list[UUID],
    db: Session = Depends(get_db),
    recruiter: Recruiter = Depends(get_current_recruiter),
):
    # --------------------------------------------------
    # FETCH JOB (OWNER ONLY)
    # --------------------------------------------------
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == recruiter.id,
    ).first()

    if not job:
        raise HTTPException(403, "Only job owner can share")

    # --------------------------------------------------
    # SHARE + EMAIL LOOP
    # --------------------------------------------------
    for rid in recruiter_ids:

        # ---------------- DB SHARE ----------------
        db.merge(
            JobShare(
                job_id=job.id,
                owner_recruiter_id=recruiter.id,
                shared_with_recruiter_id=rid,
            )
        )

        # ---------------- FETCH TARGET RECRUITER ----------------
        target_recruiter = db.query(Recruiter).filter(
            Recruiter.id == rid
        ).first()

        if not target_recruiter or not target_recruiter.user:
            continue

        # --------------------------------------------------
        # EMAIL CONTENT FROM TEMPLATE
        # --------------------------------------------------
        subject, body = job_shared(
            job.title,
            recruiter.user.full_name
        )

        # --------------------------------------------------
        # SEND EMAIL (SAFE)
        # --------------------------------------------------
        try:
            send_email(
                to_email=target_recruiter.user.email,
                subject=subject,
                body=body,
            )

        except Exception as e:
            # Email failure should NOT break sharing
            print("Email sending failed:", e)

    # --------------------------------------------------
    # COMMIT ALL SHARES
    # --------------------------------------------------
    db.commit()

    return {"message": "Job shared successfully"}
# --------------------------------------------------
# JOBS SHARED WITH CURRENT RECRUITER
# --------------------------------------------------
@router.get("/shared-with-me")
def jobs_shared_with_me(
    db: Session = Depends(get_db),
    recruiter: Recruiter = Depends(get_current_recruiter),
):
    jobs = (
        db.query(Job)
        .join(JobShare, Job.id == JobShare.job_id)
        .filter(JobShare.shared_with_recruiter_id == recruiter.id)
        .order_by(Job.created_at.desc())
        .all()
    )

    return [
        {
            "job_id": job.id,
            "title": job.title,
            "location": job.location,
        }
        for job in jobs
    ]