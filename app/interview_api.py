from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, date
from .schemas import ScheduleInterviewRequest


from .db import get_db
from .models import (
    Interview,
    Interviewer,
    InterviewInterviewer,
    InterviewSlot,
    Application,
    ApplicationStatus,
    User,
    UserRole,
    
)
from .auth_api import oauth2_scheme, decode_cognito_token
from .email_utils import send_email
from .email_templates import interview_slot_confirmed
router = APIRouter(prefix="/interviews", tags=["Interviews"])

PORTAL_URL = "http://localhost:8501"  # 👈 change when deployed

# =====================================================
# 📅 CREATE INTERVIEW (SEND SLOTS FLOW)
@router.post("/schedule")
def schedule_interview(
    payload: ScheduleInterviewRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload_token = decode_cognito_token(token)

    recruiter_user = db.query(User).filter(
        User.cognito_sub == payload_token["sub"],
        User.role == UserRole.recruiter
    ).first()

    if not recruiter_user:
        raise HTTPException(403, "Only recruiters can schedule interviews")

    application = db.query(Application).filter(
        Application.id == payload.application_id
    ).first()

    if not application:
        raise HTTPException(404, "Application not found")

    if application.status != ApplicationStatus.shortlisted:
        raise HTTPException(400, "Candidate must be shortlisted")

    if application.interview:
        raise HTTPException(400, "Interview already exists")

    if payload.interview_type not in ["online", "offline", "telephone"]:
        raise HTTPException(400, "Invalid interview type")

    interview = Interview(
        application_id=application.id,
        interview_type=payload.interview_type,
        meeting_link=payload.meeting_link,
        location=payload.location,
        scheduled_at=None,
    )

    # 🔑 DIRECT MODE
    if payload.schedule_mode == "direct":
        if not payload.scheduled_at:
            raise HTTPException(400, "scheduled_at required for direct interview")
        interview.scheduled_at = payload.scheduled_at

    db.add(interview)
    application.status = ApplicationStatus.interview
    db.commit()
    db.refresh(interview)

    # Map interviewers
    for interviewer_id in payload.interviewer_ids:
        db.add(
            InterviewInterviewer(
                interview_id=interview.id,
                interviewer_id=interviewer_id
            )
        )
    db.commit()
    db.refresh(interview)

    # --------------------------------------------------
    # 📩 DIRECT MODE EMAIL + RESUME
    # --------------------------------------------------
    if payload.schedule_mode == "direct":
        from .email_utils import get_resume_bytes, send_email_with_attachment

        candidate = application.candidate.user
        job = application.job

        resume = application.resume
        resume_bytes = None
        filename = None

        if resume:
            resume_bytes = get_resume_bytes(resume.resume_s3_key)
            filename = resume.original_filename or "resume.pdf"

        subject = f"Interview Scheduled – {job.title}"
        body = f"""
Hi {candidate.full_name},

Your interview has been scheduled.

Job Role: {job.title}
Interview Type: {interview.interview_type.title()}
Date & Time: {interview.scheduled_at}

Interview Details:
{interview.meeting_link or interview.location}

Regards,
Recruitment Team
"""

        # Candidate
        if resume_bytes:
            send_email_with_attachment(
                candidate.email, subject, body, resume_bytes, filename
            )
        else:
            send_email(candidate.email, subject, body)

        # Interviewers
        for interviewer in interview.interviewers:
            if resume_bytes:
                send_email_with_attachment(
                    interviewer.email, subject, body, resume_bytes, filename
                )
            else:
                send_email(interviewer.email, subject, body)

    return {
        "message": "Interview scheduled successfully",
        "interview_id": str(interview.id),
        "schedule_mode": payload.schedule_mode
    }

# =====================================================
# 🔄 RESCHEDULE INTERVIEW (RECRUITER)
# =====================================================
@router.put("/reschedule/{application_id}")
def reschedule_interview(
    application_id: UUID,
    new_scheduled_at: datetime,
    new_meeting_link: str | None = None,

    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    user = db.query(User).filter(
        User.cognito_sub == payload["sub"]
    ).first()

    if not user or user.role != UserRole.recruiter:
        raise HTTPException(403, "Only recruiters can reschedule interviews")

    interview = db.query(Interview).filter(
        Interview.application_id == application_id
    ).first()

    if not interview:
        raise HTTPException(404, "Interview not found")

    old_date = interview.scheduled_at
    interview.scheduled_at = new_scheduled_at

    if interview.interview_type == "online":
        interview.meeting_link = new_meeting_link or interview.meeting_link

    db.commit()
    db.refresh(interview)

    application = interview.application
    candidate = application.candidate.user

    resume = application.resume
    resume_bytes = None
    filename = None

    if resume:
        resume_bytes = get_resume_bytes(resume.resume_s3_key)
        filename = resume.original_filename or "resume.pdf"

    subject, body = interview_rescheduled(
        candidate_name=candidate.full_name,
        job_title=application.job.title,
        interview_type=interview.interview_type,
        old_datetime=old_date,
        new_datetime=new_scheduled_at,
        meeting_link=interview.meeting_link,
        location=interview.location,
        phone_number=interview.phone_number,
    )

    if resume_bytes:
        send_email_with_attachment(
            to_email=candidate.email,
            subject=subject,
            body=body,
            file_bytes=resume_bytes,
            filename=filename,
        )
    else:
        send_email(
            to_email=candidate.email,
            subject=subject,
            body=body,
        )

    return {"message": "Interview rescheduled successfully"}


# =====================================================
# ❌ CANCEL INTERVIEW (RECRUITER)
# =====================================================
@router.put("/cancel/{application_id}")
def cancel_interview_by_recruiter(
    application_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    recruiter_user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.recruiter
    ).first()

    if not recruiter_user:
        raise HTTPException(403, "Only recruiters can cancel interviews")

    interview = db.query(Interview).filter(
        Interview.application_id == application_id
    ).first()

    if not interview:
        raise HTTPException(404, "Interview not found")

    # ---------------- CANCEL ----------------
    interview.status = "cancelled"
    interview.scheduled_at = None
    interview.application.status = ApplicationStatus.rejected

    db.commit()

    # ---------------- EMAIL ALL ----------------
    notify_all_on_cancel(
        interview=interview,
        cancelled_by="recruiter"
    )

    return {
        "message": "Interview cancelled successfully and notifications sent"
    }


# =====================================================
# ❌ CANCEL INTERVIEW (CANDIDATE)
# =====================================================
@router.put("/cancel-by-candidate/{application_id}")
def cancel_interview_by_candidate(
    application_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    candidate_user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.user
    ).first()

    if not candidate_user:
        raise HTTPException(403, "Only candidates can cancel interviews")

    interview = db.query(Interview).filter(
        Interview.application_id == application_id
    ).first()

    if not interview:
        raise HTTPException(404, "Interview not found")

    # ---------------- CANCEL ----------------
    interview.status = "cancelled"
    interview.scheduled_at = None
    interview.application.status = ApplicationStatus.rejected

    db.commit()

    # ---------------- EMAIL ALL ----------------
    notify_all_on_cancel(
        interview=interview,
        cancelled_by="candidate"
    )

    return {
        "message": "Interview cancelled successfully and notifications sent"
    }

@router.post("/slots/{interview_id}")
def add_interview_slots(
    interview_id: UUID,
    interview_date: date,
    slots: list[dict] = Body(...),  # [{start_time, end_time}]
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    recruiter = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.recruiter
    ).first()

    if not recruiter:
        raise HTTPException(403, "Only recruiters allowed")

    interview = db.query(Interview).filter(
        Interview.id == interview_id
    ).first()

    if not interview:
        raise HTTPException(404, "Interview not found")

    interview.slots.clear()

    for slot in slots:
        start_dt = datetime.combine(
            interview_date,
            datetime.strptime(slot["start_time"], "%H:%M").time()
        )
        end_dt = datetime.combine(
            interview_date,
            datetime.strptime(slot["end_time"], "%H:%M").time()
        )

        db.add(
            InterviewSlot(
                interview_id=interview.id,
                start_time=start_dt,
                end_time=end_dt
            )
        )

    db.commit()

    candidate = interview.application.candidate.user
    job = interview.application.job

    # 📩 SLOT SELECTION EMAIL
    send_email(
        to_email=candidate.email,
        subject=f"Select Interview Slot – {job.title}",
        body=f"""
Hi {candidate.full_name},

You have been shortlisted for the position of {job.title}.

The recruiter has shared multiple interview time slots.
Please log in to the portal and select one convenient slot.

👉 {PORTAL_URL}/my-applications

Interview Type: {interview.interview_type.title()}

Regards,
Recruitment Team
"""
    )

    return {"message": "Interview slots sent to candidate"}
@router.get("/slots/{application_id}")
def get_interview_slots(
    application_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    user = db.query(User).filter(User.cognito_sub == payload["sub"]).first()
    if not user or user.role != UserRole.user:
        raise HTTPException(403, "Only candidates allowed")

    interview = db.query(Interview).filter(
        Interview.application_id == application_id
    ).first()

    if not interview:
        raise HTTPException(404, "Interview not found")

    return [
        {
            "slot_id": str(slot.id),
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "is_selected": slot.is_selected,
        }
        for slot in interview.slots
    ]

@router.put("/slots/select/{slot_id}")
def select_interview_slot(
    slot_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    candidate_user = db.query(User).filter(
        User.cognito_sub == payload["sub"],
        User.role == UserRole.user
    ).first()

    if not candidate_user:
        raise HTTPException(403, "Only candidates can select slots")

    slot = db.query(InterviewSlot).filter(
        InterviewSlot.id == slot_id
    ).first()

    if not slot:
        raise HTTPException(404, "Slot not found")

    interview = slot.interview
    application = interview.application

    if interview.scheduled_at:
        raise HTTPException(400, "Interview already confirmed")

    # Unselect all
    db.query(InterviewSlot).filter(
        InterviewSlot.interview_id == interview.id
    ).update({"is_selected": False})

    slot.is_selected = True
    interview.scheduled_at = slot.start_time

    db.commit()
    db.refresh(interview)

    # ---------------- DETAILS ----------------
    details = f"""
Job Role: {application.job.title}
Candidate Name: {candidate_user.full_name}
Interview Type: {interview.interview_type.title()}
Date & Time: {interview.scheduled_at}
"""

    if interview.interview_type == "online":
        details += f"\nMeeting Link:\n{interview.meeting_link}"
    elif interview.interview_type == "offline":
        details += f"\nLocation:\n{interview.location}"
    else:
        details += "\nInterview via phone call"

    # ---------------- RESUME ----------------
    from .email_utils import get_resume_bytes, send_email_with_attachment

    resume = application.resume
    resume_bytes = None
    filename = None

    if resume:
        resume_bytes = get_resume_bytes(resume.resume_s3_key)
        filename = resume.original_filename or "resume.pdf"

    subject = f"Interview Confirmed – {application.job.title}"

    body = f"""
Hi {candidate_user.full_name},

Your interview slot has been confirmed 🎉

Interview Details
-----------------
{details}

Regards,
Recruitment Team
"""

    # Candidate email
    if resume_bytes:
        send_email_with_attachment(
            candidate_user.email, subject, body, resume_bytes, filename
        )
    else:
        send_email(candidate_user.email, subject, body)

    # Interviewers email
    for interviewer in interview.interviewers:
        if resume_bytes:
            send_email_with_attachment(
                interviewer.email, subject, body, resume_bytes, filename
            )
        else:
            send_email(interviewer.email, subject, body)

    return {"message": "Interview slot confirmed successfully"}

def notify_all_on_cancel(interview, reason):
    candidate = interview.application.candidate.user
    recruiter = interview.application.job.recruiter.user
    interviewers = interview.interviewers

    emails = {
        candidate.email,
        recruiter.email,
        *[i.email for i in interviewers]
    }

    for email in emails:
        send_email(
            to_email=email,
            subject="Interview Cancelled",
            body=reason
        )
