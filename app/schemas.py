from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr,ConfigDict,Field
from enum import Enum

from .models import (
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


# =====================================================
# SIGNUP
# =====================================================

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
    current_location: Optional[str]
    preferred_location: Optional[str]
    total_experience: Optional[float]
    current_ctc: Optional[float]
    expected_ctc: Optional[float]
    profile_summary: Optional[str]
    resume_headline: Optional[str]
    notice_period: Optional[str]
    willing_to_relocate: Optional[bool]
    preferred_shift: Optional[str]
    employment_type_preference: Optional[str]
    linkedin_url: Optional[str]
    github_url: Optional[str]
    portfolio_url: Optional[str]
    visibility: str = "public"


class CandidateProfileCreate(CandidateProfileBase):
    """
    user_id is derived from authenticated user
    """
    pass

class CandidateProfileUpdate(BaseSchema):
    current_location: Optional[str] = None
    preferred_location: Optional[str] = None
    total_experience: Optional[float] = None
    current_ctc: Optional[float] = None
    expected_ctc: Optional[float] = None
    profile_summary: Optional[str] = None
    phone_number: Optional[str] = None

    resume_headline: Optional[str] = Field(None, max_length=200)
    public_username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=30,
        pattern="^[a-zA-Z0-9_]+$"
    )
    notice_period: Optional[str] = None
    willing_to_relocate: Optional[bool] = None
    preferred_shift: Optional[str] = None
    employment_type_preference: Optional[str] = None

    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    visibility: Optional[str] = None

class CandidateProfileRead(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    email: str
    phone_number: Optional[str]

    profile_picture: Optional[str]
    current_location: Optional[str]
    preferred_location: Optional[str]
    total_experience: Optional[float]
    current_ctc: Optional[float]
    expected_ctc: Optional[float]
    profile_summary: Optional[str]
    resume_headline: Optional[str]

    public_username: str   # ✅ REQUIRED

    visibility: str
    linkedin_url: Optional[str]
    github_url: Optional[str]
    portfolio_url: Optional[str]

    last_active: Optional[datetime]
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
    candidate_id: UUID


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
    candidate_id: UUID


# =====================================================
# SKILL MASTER
# =====================================================

class SkillRead(BaseSchema):
    id: UUID
    name: str


# =====================================================
# CANDIDATE SKILLS
# =====================================================

class CandidateSkillInput(BaseSchema):
    name: str
    proficiency: Optional[str] = None
    years_of_experience: Optional[float] = None

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
    description: Optional[str] = None
    location: Optional[str] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    employment_type: Optional[str] = None
    status: JobStatus = JobStatus.draft


class JobCreate(BaseSchema):
    title: str
    description: Optional[str] = None
    description_file_key: Optional[str] = None
    location: Optional[str]
    min_experience: Optional[float]
    max_experience: Optional[float]
    salary_min: Optional[float]
    salary_max: Optional[float]
    employment_type: Optional[str]
    skills: List[str]


class JobUpdate(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    employment_type: Optional[str] = None
    status: Optional[JobStatus] = None
    skills: Optional[List[str]] = None   # 🔥 REQUIRED

class JobRead(JobBase):
    id: UUID
    recruiter_id: UUID
    company_id: UUID
    is_active: bool
    created_at: datetime
    skills: list[str] = []  


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
# JOB DESCRIPTION
# =====================================================

class JobDescriptionCreate(BaseSchema):
    title: str
    description_text: Optional[str] = None
    experience_level: Optional[str] = None
    job_type: Optional[str] = None
    location: Optional[str] = None
    skill_ids: Optional[list[UUID]] = []


class JobDescriptionRead(BaseSchema):
    id: UUID
    title: str
    description_text: Optional[str]
    description_file_key: Optional[str]
    experience_level: Optional[str]
    job_type: Optional[str]
    location: Optional[str]
    is_active: bool
    created_at: datetime

class JobResponse(BaseModel):
    id: UUID
    title: str
    description: str
    description_file_key: Optional[str] = None
    location: Optional[str]
    min_experience: Optional[float]
    max_experience: Optional[float]
    salary_min: Optional[float]
    salary_max: Optional[float]
    employment_type: Optional[str]

    model_config = ConfigDict(from_attributes=True)

# =====================================================
# PROFILE ANALYTICS
# =====================================================

class ProfileCompletion(BaseSchema):
    percentage: int
    missing_sections: list[str]
    suggestions: list[str]
    is_complete: bool
    score_breakdown: dict[str, int]


class ProfileAnalytics(BaseSchema):
    profile_views: int
    recent_views: int
    total_applications: int
    saved_jobs: int
    application_breakdown: dict[str, int]
    profile_completion: int
    profile_score: int


# =====================================================
# RESUME
# =====================================================

class ResumeCreate(BaseSchema):
    resume_s3_key: str
    is_primary: bool = True


class ResumeRead(BaseSchema):
    id: UUID
    candidate_id: UUID
    resume_s3_key: str
    is_primary: bool
    uploaded_at: datetime


# =====================================================
# APPLICATION
# =====================================================

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
    candidate_notes: Optional[str] = None



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
    
    
class ScheduleInterviewRequest(BaseModel):
    application_id: UUID

    # 🔑 NEW
    schedule_mode: str          # "direct" | "slots"

    interview_type: str         # online | offline | telephone

    # DIRECT MODE
    scheduled_at: Optional[datetime] = None

    # SLOT MODE
    interview_date: Optional[str] = None

    interviewer_ids: List[UUID]

    meeting_link: Optional[str] = None
    location: Optional[str] = None

class InterviewerCreate(BaseModel):
    name: str
    email: EmailStr
    
    
class JobApplicationQuestionCreate(BaseModel):
    question_text: str
    field_type: str                 # text | textarea | select | boolean
    options: Optional[List[str]] = None
    is_required: bool = False
    order_index: int = 0
    
class JobApplicationQuestionRead(BaseModel):
    id: UUID
    question_text: str
    field_type: str
    options: Optional[List[str]]
    is_required: bool
    order_index: int

    class Config:
        from_attributes = True
        
        
class JobApplicationAnswerCreate(BaseModel):
    question_id: UUID
    answer: str