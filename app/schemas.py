from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models import (
    UserRole,
    JobStatus,
    ApplicationStatus,
    InterviewStatus,
)


# =====================================================
# BASE CONFIG
# =====================================================

class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}



class CompleteSignupSchema(BaseSchema):
    sub: str
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    role: UserRole

    # recruiter-only
    company_name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    designation: Optional[str] = None

# =====================================================
# USER
# =====================================================

class UserCreate(BaseSchema):
    cognito_sub: str
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    role: UserRole


class UserRead(BaseSchema):
    id: UUID
    full_name: str
    email: EmailStr
    phone_number: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime


# =====================================================
# CANDIDATE PROFILE
# =====================================================

class CandidateProfileBase(BaseSchema):
    current_location: Optional[str] = None
    preferred_location: Optional[str] = None
    total_experience: Optional[float] = None
    current_ctc: Optional[float] = None
    expected_ctc: Optional[float] = None
    profile_summary: Optional[str] = None
    visibility: str = "public"


class CandidateProfileCreate(CandidateProfileBase):
    """
    user_id is derived from authenticated user (JWT / Cognito),
    NOT accepted from client.
    """
    pass


class CandidateProfileRead(CandidateProfileBase):
    id: UUID
    user_id: UUID
    full_name: str 
    email: EmailStr
    profile_picture: Optional[str] = None
    current_location: Optional[str]
    preferred_location: Optional[str]
    total_experience: Optional[float]
    current_ctc: Optional[float]
    expected_ctc: Optional[float]
    profile_summary: Optional[str]
    visibility: str
    is_active: bool
    created_at: datetime


# =====================================================
# EDUCATION
# =====================================================

class CandidateEducationBase(BaseSchema):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade: Optional[str] = None


class CandidateEducationCreate(CandidateEducationBase):
    pass


class CandidateEducationRead(CandidateEducationBase):
    id: UUID
    candidate_id: UUID


# =====================================================
# EXPERIENCE
# =====================================================


class CandidateExperienceCreate(BaseSchema):
    company_name: str
    role: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: bool = False
    description: Optional[str] = None


class CandidateExperienceRead(CandidateExperienceCreate):
    id: UUID

# =====================================================
# PROJECTS
# =====================================================

# =====================================================
# PROJECTS
# =====================================================

class CandidateProjectBase(BaseSchema):
    title: str
    description: Optional[str] = None
    technologies_used: Optional[str] = None
    project_url: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CandidateProjectCreate(CandidateProjectBase):
    pass


class CandidateProjectRead(CandidateProjectBase):
    id: UUID



# =====================================================
# SKILL MASTER
# =====================================================

class SkillRead(BaseSchema):
    id: UUID
    name: str


# =====================================================
# CANDIDATE SKILLS
# =====================================================

class CandidateSkillBase(BaseSchema):
    proficiency: Optional[str] = None
    years_of_experience: Optional[float] = None


class CandidateSkillCreate(CandidateSkillBase):
    skill_id: UUID


class CandidateSkillRead(CandidateSkillBase):
    id: UUID
    skill_id: UUID



# =====================================================
# COMPANY
# =====================================================

class CompanyCreate(BaseSchema):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class CompanyRead(CompanyCreate):
    id: UUID
    is_active: bool
    created_at: datetime


# =====================================================
# RECRUITER
# =====================================================

class RecruiterCreate(BaseSchema):
    user_id: UUID
    company_id: UUID
    designation: Optional[str] = None


class RecruiterRead(BaseSchema):
    id: UUID
    user_id: UUID
    company_id: UUID
    designation: Optional[str]
    is_active: bool
    created_at: datetime


# =====================================================
# JOB
# =====================================================

class JobBase(BaseSchema):
    title: str
    description: str
    location: Optional[str] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    employment_type: Optional[str] = None
    status: JobStatus = JobStatus.draft

class JobCreate(JobBase):
    """
    recruiter_id and company_id are derived from logged-in recruiter
    """
    pass

class JobRead(JobBase):
    id: UUID
    recruiter_id: UUID
    company_id: UUID
    is_active: bool
    created_at: datetime


# =====================================================
# JOB SKILLS
# =====================================================

class JobSkillCreate(BaseSchema):
    job_id: UUID
    skill_id: UUID
    min_experience: Optional[float] = None
    mandatory: bool = True


class JobSkillRead(JobSkillCreate):
    id: UUID


# =====================================================
# RESUME
# =====================================================

class ResumeCreate(BaseSchema):
    resume_s3_key: str
    is_primary: bool = True   # ✅ MATCHES DB DEFAULT


class ResumeRead(BaseSchema):
    id: UUID
    candidate_id: UUID
    resume_s3_key: str
    is_primary: bool
    uploaded_at: datetime


# =====================================================
# APPLICATION
# =====================================================

class ApplicationCreate(BaseSchema):
    job_id: UUID
    candidate_id: UUID
    resume_id: Optional[UUID] = None


class ApplicationRead(BaseSchema):
    id: UUID
    job_id: UUID
    candidate_id: UUID
    resume_id: Optional[UUID]
    status: ApplicationStatus
    applied_at: datetime


# =====================================================
# INTERVIEW
# =====================================================

class InterviewCreate(BaseSchema):
    application_id: UUID
    scheduled_at: Optional[datetime] = None
    meeting_link: Optional[str] = None


class InterviewRead(BaseSchema):
    id: UUID
    application_id: UUID
    scheduled_at: Optional[datetime]
    meeting_link: Optional[str]
    status: InterviewStatus
    created_at: datetime
