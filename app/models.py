import enum
import uuid
from sqlalchemy import (
    Column,
    String,
    Enum,
    ForeignKey,
    DateTime,
    Boolean,
    Text,
    Float,
    Integer,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON

from .db import Base


# =====================================================
# ENUMS
# =====================================================

class UserRole(str, enum.Enum):
    user = "user"
    recruiter = "recruiter"


class JobStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    closed = "closed"


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    shortlisted = "shortlisted"
    interview = "interview"
    offered = "offered"
    rejected = "rejected"


class InterviewStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


# =====================================================
# USER
# =====================================================

class User(Base):
    __tablename__= "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cognito_sub = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20))

    role = Column(Enum(UserRole, name="user_role"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate_profile = relationship(
        "CandidateProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    recruiter_profile = relationship(
        "Recruiter",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


# =====================================================
# CANDIDATE PROFILE
# =====================================================


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True
    )

    profile_picture = Column(String(500))

    current_location = Column(String(255), index=True)
    preferred_location = Column(String(255), index=True)
    total_experience = Column(Float, index=True)
    current_ctc = Column(Float)
    expected_ctc = Column(Float)

    profile_summary = Column(Text)
    resume_headline = Column(String(500))
    notice_period = Column(String(50))
    willing_to_relocate = Column(Boolean, default=False)
    preferred_shift = Column(String(50))
    employment_type_preference = Column(String(100))
    public_username = Column(String(100), unique=True, index=True)

    linkedin_url = Column(String(500))
    github_url = Column(String(500))
    portfolio_url = Column(String(500))

    visibility = Column(String(20), default="public")
    last_active = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="candidate_profile")

    educations = relationship(
        "CandidateEducation",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="desc(CandidateEducation.start_year)"
    )

    experiences = relationship(
        "CandidateExperience",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="desc(CandidateExperience.start_date)"
    )

    projects = relationship(
        "CandidateProject",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="desc(CandidateProject.created_at)"
    )

    skills = relationship(
        "CandidateSkill",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )

    resumes = relationship(
        "Resume",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    applications = relationship(
        "Application",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )

    saved_jobs = relationship(
        "SavedJob",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )


# =====================================================
# CANDIDATE EDUCATION
# =====================================================

class CandidateEducation(Base):
    __tablename__ = "candidate_education"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    institution = Column(String(255), nullable=False)
    degree = Column(String(255))
    field_of_study = Column(String(255))
    start_year = Column(Integer)
    end_year = Column(Integer)
    grade = Column(String(50))

    candidate = relationship("CandidateProfile", back_populates="educations")


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company_name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)

    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_current = Column(Boolean, default=False)

    description = Column(Text)

    candidate = relationship("CandidateProfile", back_populates="experiences")


# =====================================================
# CANDIDATE PROJECTS
# =====================================================

class CandidateProject(Base):
    __tablename__ = "candidate_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text)
    technologies_used = Column(String(255))
    project_url = Column(String(500))

    start_date = Column(DateTime)
    end_date = Column(DateTime)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("CandidateProfile", back_populates="projects")


# =====================================================
# COMPANY
# =====================================================

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    industry = Column(String(255))
    website = Column(String(255))
    location = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recruiters = relationship("Recruiter", back_populates="company", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")

    _table_args_ = (
        Index("idx_company_name", "name"),
        Index("idx_company_industry", "industry"),
    )


# =====================================================
# RECRUITER
# =====================================================

class Recruiter(Base):
    __tablename__ = "recruiters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    assigned_applications = relationship(
    "Application",
    foreign_keys="[Application.assigned_recruiter_id]"
    )


    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    designation = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="recruiter_profile")
    company = relationship("Company", back_populates="recruiters")
    jobs = relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")


# =====================================================
# JOB
# =====================================================

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    recruiter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.id", ondelete="CASCADE"),
        index=True,
    )
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
    )

    title = Column(String(255), nullable=False, index=True)

    # 🔧 FIX 1: allow text OR file
    description = Column(Text, nullable=True)

    # 🔧 FIX 2: store S3 file key
    description_file_key = Column(String(512), nullable=True)

    location = Column(String(255), index=True)

    min_experience = Column(Float, index=True)
    max_experience = Column(Float)
    salary_min = Column(Float, index=True)
    salary_max = Column(Float)
    employment_type = Column(String(50))

    status = Column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.draft,
        index=True,
    )
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recruiter = relationship("Recruiter", back_populates="jobs")
    company = relationship("Company", back_populates="jobs")

    applications = relationship(
        "Application",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    job_skills = relationship(
        "JobSkill",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    saved_by = relationship(
        "SavedJob",
        back_populates="job",
        cascade="all, delete-orphan",
    )

# =====================================================
# JOB SKILLS
# =====================================================

class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)

# =====================================================
# CANDIDATE SKILLS
# =====================================================

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    skill_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    proficiency = Column(String(50))
    years_of_experience = Column(Float)

    candidate = relationship("CandidateProfile", back_populates="skills")
    skill = relationship("Skill")

    __table_args__ = (
        UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
    )




class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    skill_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )

    min_experience = Column(Float)
    mandatory = Column(Boolean, default=True)

    job = relationship("Job", back_populates="job_skills")
    skill = relationship("Skill")

    _table_args_ = (
        UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),
    )


# =====================================================
# JOB DESCRIPTION MASTER
# =====================================================

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title = Column(String(255), nullable=False, index=True)

    # Either rich text OR uploaded file
    description_text = Column(Text, nullable=True)
    description_file_key = Column(String(512), nullable=True)

    # Metadata
    experience_level = Column(String(50), nullable=True)
    job_type = Column(String(50), nullable=True)
    location = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# =====================================================
# JOB DESCRIPTION ↔ SKILLS (MANY TO MANY)
# =====================================================

class JobDescriptionSkill(Base):
    __tablename__ = "job_description_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_description_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
    )

    skill_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
    )


class JobShare(Base):
    __tablename__ = "job_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner_recruiter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.id", ondelete="CASCADE"),
        nullable=False,
    )

    shared_with_recruiter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "shared_with_recruiter_id",
            name="uq_job_share",
        ),
    )

# =====================================================
# RESUME
# =====================================================

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    resume_s3_key = Column(String(500), nullable=False)

    # ================= EXISTING =================
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer)
    content_type = Column(String(100))

    is_primary = Column(Boolean, default=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # ================= NEW (ADDED – REQUIRED) =================
    display_name = Column(String(255), nullable=True)
    tags = Column(String(255), nullable=True)

    share_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    parsed_text = Column(Text, nullable=True)

    # ================= RELATIONSHIP =================
    candidate = relationship("CandidateProfile", back_populates="resumes")
    downloaded_count = Column(Integer, default=0)

# ====================================================
# APPLICATION
# =====================================================


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False
    )

    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False
    )

    resume_id = Column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id"),
        nullable=False
    )
    

    status = Column(
    Enum(ApplicationStatus, name="application_status"),
    default=ApplicationStatus.applied
    )

    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    candidate_notes = Column(Text, nullable=True)
    recruiter_notes = Column(Text, nullable=True)
    viewed_at = Column(DateTime, nullable=True)
    assigned_recruiter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.id"),
        nullable=True,
        index=True
    )

    assigned_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    assigned_at = Column(DateTime(timezone=True))

    # 🔥 THIS LINE FIXES YOUR ERROR
    interview = relationship(
        "Interview",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Existing relationships (keep them)
    job = relationship("Job", back_populates="applications")
    candidate = relationship("CandidateProfile", back_populates="applications")
    resume = relationship("Resume")
    assigned_recruiter = relationship("Recruiter")


# ============================
# APPLICATION FORM 
# =========================





# =====================================================
# SAVED JOBS
# =====================================================

class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    saved_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("CandidateProfile", back_populates="saved_jobs")
    job = relationship("Job", back_populates="saved_by")

    _table_args_ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_saved_job"),
    )


# =====================================================
# INTERVIEW
# =====================================================

# =====================================================
# INTERVIEW
# =====================================================
class Interview(Base):
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interview_type = Column(
        Enum("online", "offline", "telephone", name="interview_type"),
        nullable=False
    )

    # ✅ Final interview time (after slot selection)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)

    # Optional details
    meeting_link = Column(String(500))      # online
    location = Column(String(500))          # offline
    phone_number = Column(String(50))       # telephone

    status = Column(
        Enum("scheduled", "rescheduled", "cancelled", name="interview_status"),
        default="scheduled"
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ---------------- RELATIONSHIPS ----------------
    application = relationship("Application", back_populates="interview")

    slots = relationship(
        "InterviewSlot",
        back_populates="interview",
        cascade="all, delete-orphan"
    )

    # ✅ THIS WAS MISSING (CRITICAL)
    interviewers = relationship(
        "Interviewer",
        secondary="interview_interviewers",
        back_populates="interviews"
    )

class Interviewer(Base):
    __tablename__ = "interviewers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)

    # ✅ Make email unique (VERY IMPORTANT)
    email = Column(String(255), nullable=False, unique=True)

    # ✅ Back reference to interviews
    interviews = relationship(
        "Interview",
        secondary="interview_interviewers",
        back_populates="interviewers"
    )
    
class InterviewInterviewer(Base):
    __tablename__ = "interview_interviewers"

    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        primary_key=True,
    )

    interviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviewers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    
class InterviewSlot(Base):
    __tablename__ = "interview_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    is_selected = Column(Boolean, default=False)

    interview = relationship("Interview", back_populates="slots")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(255))
    message = Column(Text)

    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")



    
class ProfileView(Base):
    __tablename__ = "profile_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    viewed_by_recruiter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    viewed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    candidate = relationship("CandidateProfile")
    
    
    
class JobApplicationQuestion(Base):
    __tablename__ = "job_application_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question_text = Column(Text, nullable=False)

    # text | textarea | select | boolean
    field_type = Column(String(50), nullable=False)

    # Used only when field_type == "select"
    options = Column(JSON, nullable=True)

    is_required = Column(Boolean, default=False)

    order_index = Column(Integer, default=0)

    job = relationship("Job", backref="application_questions")
    answers = relationship(
        "JobApplicationAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    
class JobApplicationAnswer(Base):
    __tablename__ = "job_application_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_application_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Store answer as string (simple & flexible)
    answer = Column(Text, nullable=False)

    question = relationship(
        "JobApplicationQuestion",
        back_populates="answers",
    )
class ApplicationAssignmentHistory(Base):
    __tablename__ = "application_assignment_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_recruiter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.id"),
        nullable=True,
    )

    to_recruiter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.id"),
        nullable=False,
    )

    moved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    moved_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
