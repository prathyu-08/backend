from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func,or_
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import joinedload
from .db import get_db
from .models import User, UserRole, Job, Application, Interview, Resume, Recruiter,JobShare, CandidateProfile
from .auth_api import oauth2_scheme, decode_cognito_token

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================================================
# RECRUITER = ADMIN GUARD
# ==================================================
def get_admin_user(db: Session, token: str):
    payload = decode_cognito_token(token)
    user = db.query(User).filter(User.cognito_sub == payload["sub"]).first()

    if not user or user.role != UserRole.recruiter:
        raise HTTPException(status_code=403, detail="Recruiter access only")

    return user


# ==================================================
# TOTAL APPLICATIONS PER JOB
# ==================================================
@router.get("/applications-per-job")
def applications_per_job(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    get_admin_user(db, token)

    result = (
        db.query(
            Job.id.label("job_id"),
            Job.title.label("job_title"),
            func.count(Application.id).label("applications"),
        )
        .outerjoin(Application, Job.id == Application.job_id)
        .group_by(Job.id)
        .all()
    )

    return [
        {"job_id": r.job_id,"job_title": r.title, "applications": r.applications}
        for r in result
    ]

# ==================================================
# RECRUITER APPLICATIONS PER JOB (POSTED + SHARED)
# ==================================================
@router.get("/recruiter/applications-per-job")
def recruiter_applications_per_job(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.recruiter,
    ).first()

    
    # ✅ ADD THIS
    if not user:
        raise HTTPException(status_code=403, detail="Recruiter access only")

    recruiter = db.query(Recruiter).filter(
        Recruiter.user_id == user.id
    ).first()

    if not recruiter:
        raise HTTPException(status_code=403, detail="Recruiter profile not found")

    recruiter_id = recruiter.id

    result = (
        db.query(
            Job.id.label("job_id"),
            Job.title.label("job_title"),
            func.count(Application.id).label("applications"),
        )
        .outerjoin(Application, Job.id == Application.job_id)
        .filter(
            or_(
                Job.recruiter_id == recruiter_id,  # ✅ posted jobs
                Job.id.in_(                        # ✅ shared jobs
                    db.query(JobShare.job_id).filter(
                        JobShare.shared_with_recruiter_id == recruiter_id
                    )
                )
            )
        )
        .group_by(Job.id, Job.title)
        .all()
    )

    return [
        {
            "job_id": r.job_id,
            "job_title": r.job_title,
            "applications": r.applications,
        }
        for r in result
    ]

# ==================================================
# CANDIDATES BY STATUS
# ==================================================
@router.get("/application-status-summary")
def application_status_summary(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.recruiter,
    ).first()

    if not user:
        raise HTTPException(403, "Recruiter access only")

    recruiter = db.query(Recruiter).filter(
        Recruiter.user_id == user.id
    ).first()

    if not recruiter:
        raise HTTPException(403, "Recruiter profile not found")

    recruiter_id = recruiter.id

    result = (
        db.query(Application.status, func.count(Application.id))
        .join(Job, Application.job_id == Job.id)
        .filter(
            or_(
                Job.recruiter_id == recruiter_id,
                Job.id.in_(
                    db.query(JobShare.job_id).filter(
                        JobShare.shared_with_recruiter_id == recruiter_id
                    )
                )
            )
        )
        .group_by(Application.status)
        .all()
    )

    return {status: count for status, count in result}



# ==================================================
# UPCOMING INTERVIEWS
# ==================================================
@router.get("/upcoming-interviews")
def upcoming_interviews(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    get_admin_user(db, token)

    interviews = (
        db.query(Interview)
        .filter(Interview.scheduled_at >= datetime.utcnow())
        .order_by(Interview.scheduled_at)
        .all()
    )

    return [
        {
            "candidate": i.application.candidate.user.full_name,
            "job_title": i.application.job.title,
            "scheduled_at": i.scheduled_at,
            "meeting_link": i.meeting_link,
        }
        for i in interviews
    ]


# ==================================================
# RECENT RESUMES
# ==================================================
@router.get("/recent-resumes")
def recent_resumes(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    get_admin_user(db, token)

    resumes = (
        db.query(Resume)
        .order_by(Resume.uploaded_at.desc())
        .limit(10)
        .all()
    )

    return [
        {
            "candidate": r.candidate.user.full_name,
            "filename": r.original_filename,
            "uploaded_at": r.uploaded_at,
        }
        for r in resumes
    ]
    
# ==================================================
# CANDIDATES NEEDING ACTION
# ==================================================
@router.get("/candidates-needing-action")
def candidates_needing_action(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    get_admin_user(db, token)

    results = (
        db.query(
            User.full_name.label("candidate_name"),
            Job.title.label("job_title"),
            Application.status,
            func.date_part(
                "day",
                func.now() - Application.applied_at
            ).label("days_pending"),
        )
        .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
        .join(User, User.id == CandidateProfile.user_id)
        .join(Job, Job.id == Application.job_id)
        .filter(
            Application.status.in_([
                "applied",
                "shortlisted",
                "interview",
            ])
        )
        .order_by(func.now() - Application.applied_at.desc())
        .limit(10)
        .all()
    )

    return [
        {
            "candidate_name": r.candidate_name,
            "job_title": r.job_title,
            "status": r.status,
            "days_pending": int(r.days_pending),
        }
        for r in results
    ]
# ==================================================
# JOB PERFORMANCE (✅ MISSING FIXED)
# ==================================================
@router.get("/job-performance")
def job_performance(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    get_admin_user(db, token)

    jobs = db.query(Job).all()

    data = []
    for job in jobs:
        applications_count = (
            db.query(func.count(Application.id))
            .filter(Application.job_id == job.id)
            .scalar()
        )

        data.append({
            "job_id": job.id,
            "job_title": job.title,
            "applications": applications_count,
        })

    return data

@router.post("/assign-applications")
def assign_applications(
    payload: dict,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    data = decode_cognito_token(token)

    user = db.query(User).filter(
        User.cognito_sub == data["sub"],
        User.role == UserRole.recruiter,
    ).first()

    if not user:
        raise HTTPException(403, "Recruiter only")

    main_recruiter = user.recruiter_profile

    job = db.query(Job).filter(
        Job.id == payload["job_id"],
        Job.recruiter_id == main_recruiter.id
    ).first()

    if not job:
        raise HTTPException(
            403,
            "Only main recruiter can assign applications"
        )

    for item in payload["assignments"]:
        app = db.query(Application).filter(
            Application.id == item["application_id"],
            Application.job_id == job.id
        ).first()

        if not app:
            continue

        target_recruiter = db.query(Recruiter).filter(
            Recruiter.id == item["recruiter_id"],
            Recruiter.company_id == main_recruiter.company_id
        ).first()

        if not target_recruiter:
            continue

        app.assigned_recruiter_id = target_recruiter.id
        app.assigned_by = user.id
        app.assigned_at = datetime.utcnow()

    db.commit()

    return {"message": "Applications assigned successfully"}

@router.post("/auto-assign/{job_id}")
def auto_assign_applications(
    job_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    admin = get_admin_user(db, token)

    recruiters = (
        db.query(Recruiter)
        .filter(Recruiter.company_id == admin.recruiter_profile.company_id)
        .all()
    )

    if not recruiters:
        raise HTTPException(400, "No recruiters found")

    applications = (
        db.query(Application)
        .filter(
            Application.job_id == job_id,
            Application.assigned_recruiter_id == None
        )
        .order_by(Application.applied_at)
        .all()
    )

    if not applications:
        return {"message": "No unassigned applications"}

    for index, app in enumerate(applications):
        recruiter = recruiters[index % len(recruiters)]
        app.assigned_recruiter_id = recruiter.id
        app.assigned_by = admin.id
        app.assigned_at = datetime.utcnow()

        # Email candidate
        subject, body = recruiter_assigned(app.job.title)
        send_email(app.candidate.user.email, subject, body)

    db.commit()
    return {"message": "Applications auto-assigned successfully"}

@router.get("/recruiters")
def get_company_recruiters(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    user = db.query(User).filter(
        User.cognito_sub == payload["sub"]
    ).first()

    if not user:
        raise HTTPException(403, "User not found")

    recruiter = user.recruiter_profile

    if not recruiter:
        raise HTTPException(403, "Recruiter profile not found")

    # ✅ EAGER LOAD USER RELATIONSHIP
    recruiters = (
        db.query(Recruiter)
        .options(joinedload(Recruiter.user))
        .filter(Recruiter.company_id == recruiter.company_id)
        .all()
    )

    return [
        {
            "id": str(r.id),
            "full_name": r.user.full_name
        }
        for r in recruiters
    ]

@router.put("/assign-application/{application_id}")
def assign_single_application(
    application_id: UUID,
    recruiter_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    from datetime import datetime

    payload = decode_cognito_token(token)

    # ---------------- AUTH ----------------
    user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.recruiter,
    ).first()

    if not user:
        raise HTTPException(403, "Recruiter only")

    recruiter_profile = user.recruiter_profile

    # ---------------- GET APPLICATION ----------------
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

    # =====================================================
    # 🔐 AUTHORIZATION LOGIC (UPDATED)
    # =====================================================

    # 1️⃣ Job Owner
    is_owner = job.recruiter_id == recruiter_profile.id

    # 2️⃣ Assigned Recruiter (🔥 NEW)
    is_assigned = (
        application.assigned_recruiter_id == recruiter_profile.id
    )

    # 3️⃣ Shared Recruiter (optional — keep if needed)
    is_shared = db.query(JobShare).filter(
        JobShare.job_id == job.id,
        JobShare.shared_with_recruiter_id == recruiter_profile.id
    ).first()

    # ❌ If none → block
    if not is_owner and not is_assigned:
        raise HTTPException(
            403,
            "Only job owner or assigned recruiter can assign"
        )

    # =====================================================
    # 🎯 TARGET RECRUITER VALIDATION
    # =====================================================
    target = db.query(Recruiter).filter(
        Recruiter.id == recruiter_id,
        Recruiter.company_id == recruiter_profile.company_id
    ).first()

    if not target:
        raise HTTPException(404, "Recruiter not found")

    # =====================================================
    # ✅ ASSIGN / REASSIGN
    # =====================================================
    application.assigned_recruiter_id = recruiter_id
    application.assigned_by = user.id
    application.assigned_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Application assigned successfully",
        "application_id": application.id,
        "assigned_to": recruiter_id,
    }
