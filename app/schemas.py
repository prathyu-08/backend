from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    admin = "admin"
    recruiter = "recruiter"
    candidate = "user"

# ------------------ COMMON user ------------------
class UserRegister(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    phone_number: str
    password: str
    role: UserRole

# ------------------ RECRUITER ------------------
class RecruiterRegister(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    phone_number: str
    password: str
    company_name: str
    company_website: str
    company_location: str
    designation: str
