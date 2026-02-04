import os
from uuid import uuid4
from datetime import datetime

import boto3
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, Resume, CandidateProfile
from .auth_api import oauth2_scheme, decode_cognito_token
from .email_utils import send_email

router = APIRouter(prefix="/resume", tags=["Resume"])

AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

ALLOWED_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_RESUMES_PER_USER = 10


def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_cognito_token(token)
    user = db.query(User).filter(User.cognito_sub == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def ensure_candidate_profile(db: Session, user: User):
    if user.candidate_profile:
        return user.candidate_profile
    profile = CandidateProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def presigned_get(s3_key: str, expires=3600):
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expires,
    )


# ================= UPLOAD =================
@router.post("/upload")
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    profile = ensure_candidate_profile(db, current_user)

    if (
        db.query(Resume)
        .filter(Resume.candidate_id == profile.id)
        .count()
        >= MAX_RESUMES_PER_USER
    ):
        raise HTTPException(400, "Maximum 10 resumes allowed")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Invalid file type")

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size == 0 or size > MAX_FILE_SIZE:
        raise HTTPException(400, "Invalid file size")

    ext = file.filename.rsplit(".", 1)[-1]
    s3_key = f"resumes/{profile.id}/{uuid4()}.{ext}"

    s3.upload_fileobj(
        file.file,
        S3_BUCKET_NAME,
        s3_key,
        ExtraArgs={"ContentType": file.content_type},
    )

    resume = Resume(
        candidate_id=profile.id,
        resume_s3_key=s3_key,
        original_filename=file.filename,
        display_name=file.filename,
        file_size=size,
        content_type=file.content_type,
        is_primary=False,
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    try:
        send_email(
        current_user.email,
        "Resume Uploaded",
        "Your resume has been uploaded successfully.",
    )
    except Exception as e:
        print("SES email skipped:", str(e))


    return {"message": "Uploaded", "resume_id": str(resume.id)}


# ================= LIST =================
@router.get("/my-resumes")
def my_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    profile = ensure_candidate_profile(db, current_user)

    resumes = (
        db.query(Resume)
        .filter(Resume.candidate_id == profile.id)
        .order_by(Resume.uploaded_at.desc())
        .all()
    )

    return {
        "resumes": [
            {
                "resume_id": str(r.id),
                "filename": r.original_filename,
                "display_name": r.display_name,
                "tags": r.tags,
                "uploaded_at": str(r.uploaded_at),
                "is_primary": r.is_primary,
                "share_count": r.share_count,
                "last_accessed_at": str(r.last_accessed_at)
                if r.last_accessed_at
                else None,
            }
            for r in resumes
        ]
    }


# ================= PREVIEW / DOWNLOAD =================
@router.get("/access/{resume_id}")
def access_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    profile = ensure_candidate_profile(db, current_user)

    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.candidate_id == profile.id)
        .first()
    )
    if not resume:
        raise HTTPException(404, "Resume not found")

    resume.share_count += 1
    resume.last_accessed_at = datetime.utcnow()
    db.commit()

    return {"url": presigned_get(resume.resume_s3_key)}


# ================= RENAME =================
@router.patch("/rename/{resume_id}")
def rename_resume(
    resume_id: str,
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    profile = ensure_candidate_profile(db, current_user)
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.candidate_id == profile.id)
        .first()
    )
    if not resume:
        raise HTTPException(404, "Resume not found")

    resume.display_name = name
    db.commit()
    return {"message": "Renamed"}


# ================= TAGS =================
@router.patch("/tags/{resume_id}")
def update_tags(
    resume_id: str,
    tags: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    profile = ensure_candidate_profile(db, current_user)
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.candidate_id == profile.id)
        .first()
    )
    resume.tags = tags
    db.commit()
    return {"message": "Tags updated"}


# ================= PRIMARY =================
@router.post("/set-primary/{resume_id}")
def set_primary_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    profile = ensure_candidate_profile(db, current_user)

    db.query(Resume).filter(
        Resume.candidate_id == profile.id
    ).update({"is_primary": False})

    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.candidate_id == profile.id)
        .first()
    )
    resume.is_primary = True
    db.commit()
    return {"message": "Primary updated"}


# ================= DELETE =================
@router.delete("/delete/{resume_id}")
def delete_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    profile = ensure_candidate_profile(db, current_user)

    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.candidate_id == profile.id)
        .first()
    )

    s3.delete_object(Bucket=S3_BUCKET_NAME, Key=resume.resume_s3_key)
    db.delete(resume)
    db.commit()
    return {"message": "Deleted"}
