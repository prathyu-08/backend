from datetime import datetime

PORTAL_URL = "http://localhost:8501/my-applications"

# ==================================================
# RESUME UPLOADED
# ==================================================
def resume_uploaded():
    return (
        "Resume Uploaded Successfully",
        """
Hi,

Your resume has been uploaded successfully to the Recruitment Portal.

You can now apply for jobs and track your application status.

Regards,
Recruitment Team
"""
    )

# ==================================================
# FORGOT PASSWORD
# ==================================================
def forgot_password(link: str):
    return (
        "Reset Your Password",
        f"""
Hi,

We received a request to reset your password.

Click the link below to reset your password:
{link}

If you did not request this, please ignore this email.

Regards,
Recruitment Team
"""
    )

# ==================================================
# JOB APPLIED
# ==================================================
def job_applied(job_title: str):
    return (
        f"Application Submitted – {job_title}",
        f"""
Hi,

Your application for the position of **{job_title}** has been successfully submitted.

Our recruitment team will review your profile and get back to you if you are shortlisted.

You can track your application here:
👉 {PORTAL_URL}

Best of luck!

Regards,
Recruitment Team
"""
    )

# ==================================================
# SHORTLISTED
# ==================================================
def shortlisted(job_title: str):
    return (
        f"Shortlisted for {job_title} 🎉",
        f"""
Hi,

Congratulations! 🎉

You have been shortlisted for the position of **{job_title}**.

The next step of the hiring process will be shared with you shortly.

You can track updates here:
👉 {PORTAL_URL}

Regards,
Recruitment Team
"""
    )

# ==================================================
# REJECTED
# ==================================================
def rejected(job_title: str):
    return (
        f"Application Update – {job_title}",
        f"""
Hi,

Thank you for applying for **{job_title}**.

After careful consideration, we will not be moving forward with your application at this time.

We encourage you to apply for future opportunities that match your profile.

Regards,
Recruitment Team
"""
    )

# ==================================================
# OFFER
# ==================================================
def offer(job_title: str):
    return (
        f"Offer Letter – {job_title} 🎉",
        f"""
Hi,

Congratulations! 🎉

We are pleased to inform you that you have been selected for the position of **{job_title}**.

Our team will reach out shortly with further details.

Regards,
Recruitment Team
"""
    )

# ==================================================
# BASIC INTERVIEW (GENERIC)
# ==================================================
def interview(job_title: str, details: str):
    return (
        "Interview Scheduled",
        f"""
Hi,

Your interview for **{job_title}** is scheduled.

{details}

Regards,
Recruitment Team
"""
    )

# ==================================================
# INTERVIEW SCHEDULED (DETAILED)
# ==================================================
def interview_scheduled(
    candidate_name: str,
    job_title: str,
    interview_type: str,
    scheduled_at: str,
    meeting_link: str | None = None,
    location: str | None = None,
    phone_number: str | None = None,
):
    details = f"""
Interview Type: {interview_type.title()}
Date & Time: {scheduled_at}
"""

    if interview_type == "online" and meeting_link:
        details += f"\nMeeting Link:\n{meeting_link}"
    elif interview_type == "offline" and location:
        details += f"\nLocation:\n{location}"
    elif interview_type == "telephone" and phone_number:
        details += f"\nContact Number:\n{phone_number}"

    return (
        f"Interview Scheduled – {job_title}",
        f"""
Hi {candidate_name},

We are pleased to inform you that you have been shortlisted for the next stage
of the hiring process.

Your interview for the position of **{job_title}** has been scheduled.
Please find the details below:

{details}

Please ensure you are available on time.
If you need to reschedule or cancel, please contact us.

We wish you the very best!

Regards,
Recruitment Team
"""
    )

# ==================================================
# INTERVIEW SLOTS SHARED
# ==================================================
def interview_slots_shared(
    candidate_name: str,
    job_title: str,
    interview_type: str,
):
    return (
        f"Select Interview Slot – {job_title}",
        f"""
Hi {candidate_name},

You have been shortlisted for the position of **{job_title}**.

The recruiter has shared multiple interview time slots.
Please log in to the portal and select a slot that works best for you.

Interview Type: {interview_type.title()}

👉 Select your interview slot here:
{PORTAL_URL}

If you are unable to attend any of the slots, you may contact the recruiter through the portal.

Regards,
Recruitment Team
"""
    )

# ==================================================
# INTERVIEW SLOT CONFIRMED
# ==================================================
def interview_slot_confirmed(
    candidate_name: str,
    job_title: str,
    interview_type: str,
    scheduled_at: datetime,
    meeting_link: str | None = None,
    location: str | None = None,
):
    date_str = scheduled_at.strftime("%A, %d %B %Y")
    time_str = scheduled_at.strftime("%I:%M %p")

    details = f"""
Job Role: {job_title}
Interview Type: {interview_type.title()}
Date: {date_str}
Time: {time_str}
"""

    if interview_type == "online" and meeting_link:
        details += f"\nMeeting Link:\n{meeting_link}"
    elif interview_type == "offline" and location:
        details += f"\nInterview Location:\n{location}"
    elif interview_type == "telephone":
        details += "\nYou will receive a call on your registered phone number."

    return (
        f"Interview Slot Confirmed – {job_title}",
        f"""
Hi {candidate_name},

Your interview slot has been successfully confirmed.

Interview Details
-----------------
{details}

Need to reschedule or cancel?
You can manage your interview from the portal:
👉 {PORTAL_URL}

Please ensure you are available at least 5 minutes before the scheduled time.

Best of luck!

Regards,
Recruitment Team
"""
    )

# ==================================================
# INTERVIEW RESCHEDULED
# ==================================================
def interview_rescheduled(
    candidate_name: str,
    job_title: str,
    interview_type: str,
    old_datetime: str,
    new_datetime: str,
    meeting_link: str | None = None,
    location: str | None = None,
):
    updated_details = (
        meeting_link
        or location
        or "You will receive a call on your registered phone number."
    )

    return (
        f"Interview Rescheduled – {job_title}",
        f"""
Hi {candidate_name},

Your interview for **{job_title}** has been rescheduled.

Previous Schedule:
{old_datetime}

New Schedule:
{new_datetime}

Interview Type: {interview_type.title()}

Updated Details:
{updated_details}

You can manage your interview here:
👉 {PORTAL_URL}

Regards,
Recruitment Team
"""
    )


def application_confirmation(job_title, company_name):
    return (
        "Application Submitted Successfully ✅",
        f"""
Hi,

Your application for the position of "{job_title}" at {company_name}
has been successfully submitted.

Our hiring team will review your profile and get back to you.

Best regards,
Recruitment Team
"""
    )
