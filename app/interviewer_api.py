from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import Interviewer
from .auth_api import oauth2_scheme, decode_cognito_token

router = APIRouter(prefix="/interviewers", tags=["Interviewers"])

@router.get("/")
def list_interviewers(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    # Auth is optional, but keep for safety
    decode_cognito_token(token)

    interviewers = db.query(Interviewer).all()

    return [
        {
            "id": str(i.id),
            "name": i.name,
            "email": i.email,
        }
        for i in interviewers
    ]

@router.get("/")
def get_interviewers(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    # (Optional) restrict to recruiter/admin
    return [
        {
            "id": str(i.id),
            "name": i.name,
            "email": i.email,
        }
        for i in db.query(Interviewer).all()
    ]
