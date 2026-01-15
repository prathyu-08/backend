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
from app.db import Base


# ENUMS

class UserRole(str, enum.Enum):
    user = "user"
    recruiter = "recruiter"


class JobStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    closed = "closed"


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    viewed = "viewed"
    shortlisted = "shortlisted"
    interview = "interview"
    offered = "offered"
    rejected = "rejected"


class InterviewStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


# USER

class User(Base):
    __tablename__ = "users"

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


# CANDIDATE PROFILE

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    current_location = Column(String(255))
    preferred_location = Column(String(255))
    total_experience = Column(Float)
    current_ctc = Column(Float)
    expected_ctc = Column(Float)

    profile_summary = Column(Text)
    visibility = Column(String(20), default="public")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="candidate_profile")

    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    experiences = relationship("CandidateExperience", back_populates="candidate", cascade="all, delete-orphan")
    educations = relationship("CandidateEducation", back_populates="candidate", cascade="all, delete-orphan")
    projects = relationship("CandidateProject", back_populates="candidate", cascade="all, delete-orphan")
    preferences = relationship("CandidatePreference", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    saved_jobs = relationship("SavedJob", back_populates="candidate", cascade="all, delete-orphan")


# COMPANY

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

    __table_args__ = (
        Index("idx_company_name", "name"),
        Index("idx_company_industry", "industry"),
    )


# RECRUITER

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


# JOB

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    recruiter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(255))

    min_experience = Column(Float)
    max_experience = Column(Float)
    salary_min = Column(Float)
    salary_max = Column(Float)
    employment_type = Column(String(50))

    status = Column(Enum(JobStatus, name="job_status"), default=JobStatus.draft, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recruiter = relationship("Recruiter", back_populates="jobs")
    company = relationship("Company", back_populates="jobs")

    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    job_skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    saved_by = relationship("SavedJob", back_populates="job", cascade="all, delete-orphan")


# JOB SKILLS



class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)

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

    __table_args__ = (
        UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),
    )


# RESUME

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
    is_primary = Column(Boolean, default=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("CandidateProfile", back_populates="resumes")


# APPLICATION


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    resume_id = Column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        index=True,
    )

    status = Column(Enum(ApplicationStatus, name="application_status"), default=ApplicationStatus.applied)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="applications")
    candidate = relationship("CandidateProfile", back_populates="applications")

    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),
        Index("idx_application_status", "status"),
    )


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

    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_saved_job"),
    )


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

    scheduled_at = Column(DateTime(timezone=True))
    meeting_link = Column(String(500))
    status = Column(Enum(InterviewStatus, name="interview_status"), default=InterviewStatus.scheduled)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application")
