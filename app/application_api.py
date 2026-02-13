from fastapi import APIRouter, Depends, HTTPException,UploadFile, File, Form, Body
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from uuid import uuid4
import boto3
import os
from datetime import datetime
from .auth_api import get_current_user

from .models import Interview, Notification,JobShare
from .db import get_db
from .auth_api import oauth2_scheme, decode_cognito_token
from .notification_publisher import publish_event
from .models import (
    User,
    UserRole,
    Job,
    Application,
    ApplicationStatus,
    Recruiter,
    Resume,
    JobApplicationAnswer,
    CandidateProfile
)


router = APIRouter(prefix="/applications", tags=["Applications"])


AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),

)


@router.post("/apply")
def apply_for_job(
    job_id: str = Form(...),
    answers: str = Form(None),
    resume_id: str = Form(None),
    resume_file: UploadFile = File(None),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    token_data = decode_cognito_token(token)

    print("\n========== APPLY DEBUG START ==========")
    print("TOKEN SUB:", token_data["sub"])

    # --------------------------------------------------
    # USER VALIDATION
    # --------------------------------------------------
    user = db.query(User).filter(
        User.cognito_sub == token_data["sub"],
        User.role == UserRole.user,
    ).first()

    print("USER FOUND:", user)

    if not user:
        print("❌ USER NOT FOUND / NOT CANDIDATE")
        raise HTTPException(403, "Only candidates can apply")

    # --------------------------------------------------
    # CANDIDATE PROFILE
    # --------------------------------------------------
    candidate = user.candidate_profile
    print("CANDIDATE PROFILE:", candidate)

    if not candidate:
        print("⚠️ Candidate missing → creating profile")
        candidate = CandidateProfile(user_id=user.id)
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

    # --------------------------------------------------
    # JOB VALIDATION
    # --------------------------------------------------
    print("JOB ID RECEIVED:", job_id)

    job = db.query(Job).filter(
        Job.id == job_id,
        Job.is_active == True,
    ).first()

    print("JOB FOUND:", job)

    if not job:
        print("❌ JOB NOT FOUND / INACTIVE")
        raise HTTPException(404, "Job not found or inactive")

    # --------------------------------------------------
    # RESUME VALIDATION
    # --------------------------------------------------
    print("RESUME ID RECEIVED:", resume_id)

    if resume_id:
        resume_to_use = db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.candidate_id == candidate.id,
        ).first()

        print("RESUME FOUND:", resume_to_use)

        if not resume_to_use:
            print("❌ RESUME NOT BELONG TO CANDIDATE")
            raise HTTPException(
                404,
                "Selected resume not found for this candidate"
            )

    else:
        print("⚠️ No resume_id provided")

    print("========== APPLY DEBUG END ==========\n")

    return {"message": "Debug complete"}


# =====================================================
# 2️⃣ CANDIDATE – MY APPLICATIONS (EXTENDED)
# =====================================================
@router.get("/my")
def my_applications(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    user = db.query(User).filter(
        User.cognito_sub == payload["sub"]
    ).first()

    if not user or user.role != UserRole.user:
        raise HTTPException(403, "Not a candidate")

    candidate = user.candidate_profile
    if not candidate:
        raise HTTPException(404, "Candidate profile not found")

    applications = (
        db.query(Application)
        .options(
            joinedload(Application.job).joinedload(Job.company),
            joinedload(Application.resume) 
        )
        .filter(Application.candidate_id == candidate.id)
        .order_by(Application.applied_at.desc())
        .all()
    )

    return [
        {
            "application_id": app.id,
            "job_title": app.job.title,
            "company_name": app.job.company.name if app.job.company else None,
            "status": app.status,
            "applied_at": app.applied_at,
            "candidate_notes": app.candidate_notes,
            "resume": {
            "resume_id": app.resume.id if app.resume else None,
            "file_name": app.resume.original_filename if app.resume else None,
            "content_type": app.resume.content_type if app.resume else None,
            "uploaded_at": app.resume.uploaded_at if app.resume else None,
        },
            # Extended job info
            "job_description": app.job.description,
            "job_location": app.job.location,
            "min_experience": app.job.min_experience,
            "max_experience": app.job.max_experience,
            "salary_min": app.job.salary_min,
            "salary_max": app.job.salary_max,

            # Interview info (if exists)
            "scheduled_at": app.interview.scheduled_at if app.interview else None,
            "interview_type": app.interview.interview_type if app.interview else None,
        }
        for app in applications
    ]

@router.get("/job/{job_id}")
def view_applicants_for_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.recruiter,
    ).first()

    if not user or not user.recruiter_profile:
        raise HTTPException(403, "Recruiter only")

    # ✅ NO OWNERSHIP / COMPANY CHECK
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(404, "Job not found")

    recruiter = user.recruiter_profile

    # check owner
    is_owner = job.recruiter_id == recruiter.id

    # check shared
    is_shared = db.query(JobShare).filter(
        JobShare.job_id == job.id,
        JobShare.shared_with_recruiter_id == recruiter.id
    ).first()

    if not is_owner and not is_shared:
        raise HTTPException(403, "Not authorized to view applicants")

    applications = (
        db.query(Application)
        .options(
            joinedload(Application.candidate)
            .joinedload(CandidateProfile.user),
            joinedload(Application.interview),
        )
        .filter(Application.job_id == job_id)
        .order_by(Application.applied_at.desc())
        .all()
    )

    # =====================================================
    # MARK APPLICATION AS VIEWED + NOTIFICATION
    # =====================================================
    for app in applications:
        if app.viewed_at is None:
            app.viewed_at = datetime.utcnow()

            notification = Notification(
                user_id=app.candidate.user.id,
                title="Application Viewed",
                message=f"Your application for '{job.title}' has been viewed by the recruiter."
            )
            db.add(notification)

    db.commit()
    # =====================================================

    return {
        "job_id": str(job.id),
        "job_title": job.title,
        "is_shared_job": not is_owner,
        "applicants": [
            {
                "application_id": app.id,
                "candidate_name": app.candidate.user.full_name,
                "candidate_email": app.candidate.user.email,
                "candidate_id": app.candidate.id,
                "candidate_phone": app.candidate.user.phone_number,
                "status": app.status,
                "applied_at": app.applied_at,
                "scheduled_at": app.interview.scheduled_at if app.interview else None,
                "assigned_recruiter_id": app.assigned_recruiter_id,
            }
            for app in applications
        ],
    }



# =====================================================
# 4️⃣ RECRUITER – UPDATE APPLICATION STATUS (SNS ONLY)
# =====================================================
@router.put("/{application_id}/status")
def update_application_status(
    application_id: UUID,
    status: str,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    # ---------------- AUTH ----------------
    user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.recruiter,
    ).first()

    if not user:
        raise HTTPException(403, "Only recruiters can update status")

    recruiter = db.query(Recruiter).filter(
        Recruiter.user_id == user.id
    ).first()

    if not recruiter:
        raise HTTPException(404, "Recruiter profile not found")

    # ---------------- FETCH APPLICATION ----------------
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()

    if not application:
        raise HTTPException(404, "Application not found")

    job = db.query(Job).filter(
        Job.id == application.job_id
    ).first()

    if not job:
        raise HTTPException(404, "Job not found")

    # ---------------- AUTHORIZATION ----------------
    is_owner = job.recruiter_id == recruiter.id

    is_shared = db.query(JobShare).filter(
        JobShare.job_id == job.id,
        JobShare.shared_with_recruiter_id == recruiter.id
    ).first()

    if not is_owner and not is_shared:
        raise HTTPException(403, "Not allowed to update this application")

    # ---------------- VALIDATE STATUS ----------------
    status_clean = status.strip().lower()
    allowed = [s.value for s in ApplicationStatus]

    if status_clean not in allowed:
        raise HTTPException(
            400,
            f"Invalid status. Allowed: {allowed}"
        )

    previous_status = application.status

    # ---------------- UPDATE STATUS ----------------
    application.status = ApplicationStatus(status_clean)
    db.commit()
    db.refresh(application)

    # ---------------- 🔔 IN-APP NOTIFICATION ----------------
    from .notification_utils import create_notification

    create_notification(
        db,
        application.candidate.user.id,
        "Application Status Updated",
        f"Your application for '{job.title}' is now '{status_clean}'."
    )

    # ---------------- 🔔 SNS EVENT (REPLACED EMAIL) ----------------
    publish_event(
        "APPLICATION_STATUS_UPDATED",
        {
            "email": application.candidate.user.email,
            "candidate_name": application.candidate.user.full_name,
            "job_title": job.title,
            "new_status": status_clean,
            "previous_status": previous_status.value,
            "application_id": str(application.id),
        }
    )

    # ---------------- RESPONSE ----------------
    return {
        "message": "Application status updated successfully",
        "application_id": str(application.id),
        "previous_status": previous_status,
        "new_status": application.status,
    }
@router.put("/{application_id}/reassign")
def reassign_application(
    application_id: UUID,
    new_recruiter_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    # ---------------- AUTH ----------------
    user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.recruiter
    ).first()

    if not user or not user.recruiter_profile:
        raise HTTPException(403, "Recruiter only")

    recruiter = user.recruiter_profile

    # ---------------- FETCH APPLICATION ----------------
    app = db.query(Application).filter(
        Application.id == application_id
    ).first()

    if not app:
        raise HTTPException(404, "Application not found")

    job = db.query(Job).filter(
        Job.id == app.job_id
    ).first()

    if not job:
        raise HTTPException(404, "Job not found")

    # ---------------- AUTHORIZATION ----------------
    is_owner = job.recruiter_id == recruiter.id

    is_shared = db.query(JobShare).filter(
        JobShare.job_id == job.id,
        JobShare.shared_with_recruiter_id == recruiter.id
    ).first()

    if not is_owner and not is_shared:
        raise HTTPException(403, "Not authorized")

    # ---------------- REASSIGN ----------------
    app.assigned_recruiter_id = new_recruiter_id
    app.assigned_by = user.id
    app.assigned_at = datetime.utcnow()

    db.commit()
    db.refresh(app)

    # ---------------- 🔔 SNS EVENT (REPLACED EMAIL) ----------------
    publish_event(
        "APPLICATION_REASSIGNED",
        {
            "email": app.candidate.user.email,
            "candidate_name": app.candidate.user.full_name,
            "job_title": job.title,
            "application_id": str(app.id),
        }
    )

    return {"message": "Application reassigned successfully"}
@router.get("/assigned")
def my_assigned_applications(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.recruiter
    ).first()

    recruiter = user.recruiter_profile

    apps = (
        db.query(Application)
        .join(Job)
        .filter(Application.assigned_recruiter_id == recruiter.id)
        .order_by(Application.assigned_at.desc())
        .all()
    )

    return [
        {
            "application_id": app.id,
            "candidate_name": app.candidate.user.full_name,
            "candidate_email": app.candidate.user.email,
            "job_title": app.job.title,
            "status": app.status,
            "assigned_at": app.assigned_at,
        }
        for app in apps
    ]
@router.put("/{application_id}/candidate-notes")
def save_candidate_notes(
    application_id: UUID,
    notes: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    user = (
        db.query(User)
        .filter(
            User.cognito_sub == payload["sub"],
            User.role == UserRole.user,
        )
        .first()
    )

    if not user or not user.candidate_profile:
        raise HTTPException(status_code=403, detail="Candidate only")

    application = (
        db.query(Application)
        .filter(
            Application.id == application_id,
            Application.candidate_id == user.candidate_profile.id,
        )
        .first()
    )

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.candidate_notes = notes
    db.commit()

    return {"message": "Candidate notes saved successfully"}


@router.delete("/{job_id}/permanent", status_code=204)
def permanent_delete_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch recruiter
    recruiter = (
        db.query(Recruiter)
        .filter(Recruiter.user_id == current_user.id)
        .first()
    )

    if not recruiter:
        raise HTTPException(status_code=403, detail="Not authorized")

    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.recruiter_id == recruiter.id)
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # ❗ IMPORTANT: delete related data first
    db.query(Application).filter(Application.job_id == job_id).delete()
    db.query(Interview).filter(Interview.job_id == job_id).delete()

    # Finally delete job
    db.delete(job)
    db.commit()

