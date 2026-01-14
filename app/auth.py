from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import UserRegister, RecruiterRegister
from app.models import User, Recruiter, UserRole
from app.security import hash_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register_user(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(
        (User.username == data.username) |
        (User.email == data.email)
    ).first():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        phone_number=data.phone_number,
        hashed_password=hash_password(data.password),
        role=data.role
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User registered successfully"}


@router.post("/register/recruiter")
def register_recruiter(data: RecruiterRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(
        (User.username == data.username) |
        (User.email == data.email)
    ).first():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        phone_number=data.phone_number,
        hashed_password=hash_password(data.password),
        role=UserRole.recruiter
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    recruiter = Recruiter(
        user_id=user.id,
        company_name=data.company_name,
        company_website=data.company_website,
        company_location=data.company_location,
        designation=data.designation
    )

    db.add(recruiter)
    db.commit()

    return {"message": "Recruiter registered successfully"}
