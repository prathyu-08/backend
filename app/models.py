import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Enum,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import relationship

from app.db import Base


# ------------------ USER ROLES ------------------
class UserRole(str, enum.Enum):
    admin = "admin"
    recruiter = "recruiter"
    candidate = "user"


# ------------------ USER TABLE ------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone_number = Column(String(15))
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_verified = Column(Boolean, default=False)

    # relationships
    recruiter_profile = relationship(
        "Recruiter",
        back_populates="user",
        uselist=False,
        cascade="all, delete",
    )

    sent_emails = relationship(
        "EmailLog",
        back_populates="recruiter",
        cascade="all, delete",
    )


# ------------------ RECRUITER TABLE ------------------
class Recruiter(Base):
    __tablename__ = "recruiters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    company_name = Column(String(150), nullable=False)
    company_website = Column(String(255), nullable=False)
    company_location = Column(String(100), nullable=False)
    designation = Column(String(100), nullable=False)

    user = relationship("User", back_populates="recruiter_profile")


# ------------------ EMAIL LOG TABLE ------------------
class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)

    recruiter_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    candidate_email = Column(String(100), index=True, nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(String, nullable=False)

    sent_at = Column(DateTime, default=datetime.utcnow)

    recruiter = relationship("User", back_populates="sent_emails")
