from fastapi import APIRouter, Depends, HTTPException,UploadFile, File
from sqlalchemy.orm import Session
from uuid import UUID
from app.db import get_db
from app.utils.s3 import upload_profile_picture
from app.models import User, CandidateProfile, UserRole,CandidateEducation,CandidateExperience,CandidateSkill,Skill,UserRole,CandidateProject
from app.schemas import CandidateProfileCreate, CandidateProfileRead,CandidateEducationCreate,CandidateExperienceCreate,CandidateSkillCreate,CandidateSkillRead,CandidateProjectCreate,CandidateProjectRead
from app.auth_api import decode_cognito_token
from app.auth_api import oauth2_scheme

router = APIRouter(prefix="/candidate", tags=["Candidate"])

@router.get("/profile", response_model=CandidateProfileRead)
def get_profile(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)
    sub = payload["sub"]

    user = db.query(User).filter(User.cognito_sub == sub).first()
    if not user or user.role != UserRole.user:
        raise HTTPException(status_code=403, detail="Not a candidate")

    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 👇 MERGE USER + PROFILE
    return {
        "id": profile.id,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "current_location": profile.current_location,
        "preferred_location": profile.preferred_location,
        "total_experience": profile.total_experience,
        "current_ctc": profile.current_ctc,
        "expected_ctc": profile.expected_ctc,
        "profile_summary": profile.profile_summary,
        "visibility": profile.visibility,
        "is_active": profile.is_active,
        "created_at": profile.created_at,
    }


@router.put(
    "/profile",
    response_model=CandidateProfileRead
)
def update_profile(
    payload: CandidateProfileCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload_token = decode_cognito_token(token)
    sub = payload_token["sub"]

    user = db.query(User).filter(User.cognito_sub == sub).first()
    if not user:
        raise HTTPException(404, "User not found")

    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.id
    ).first()

    if not profile:
        raise HTTPException(404, "Profile not found")

    for key, value in payload.dict(exclude_unset=True).items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)

    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "full_name": user.full_name,
        "email": user.email,
        "profile_picture": profile.profile_picture,
        "current_location": profile.current_location,
        "preferred_location": profile.preferred_location,
        "total_experience": profile.total_experience,
        "current_ctc": profile.current_ctc,
        "expected_ctc": profile.expected_ctc,
        "profile_summary": profile.profile_summary,
        "visibility": profile.visibility,
        "is_active": profile.is_active,
        "created_at": profile.created_at,
    }

@router.post("/profile-picture")
def upload_profile_picture_api(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    # -------------------------------
    # 1️⃣ FILE TYPE VALIDATION
    # -------------------------------
    allowed_types = ["image/jpeg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG images are allowed"
        )

    # -------------------------------
    # 2️⃣ FILE SIZE VALIDATION (5 MB)
    # -------------------------------
    MAX_SIZE = 5 * 1024 * 1024  # 5 MB

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 5 MB limit"
        )

    # -------------------------------
    # 3️⃣ AUTH & OWNERSHIP CHECK
    # -------------------------------
    payload = decode_cognito_token(token)
    sub = payload["sub"]

    user = db.query(User).filter(User.cognito_sub == sub).first()
    if not user or user.role != UserRole.user:
        raise HTTPException(status_code=403, detail="Not a candidate")

    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # -------------------------------
    # 4️⃣ DELETE OLD PROFILE PICTURE (IF EXISTS)
    # -------------------------------
    if profile.profile_picture:
        from app.utils.s3 import delete_file
        delete_file(profile.profile_picture)

    # -------------------------------
    # 5️⃣ UPLOAD NEW PROFILE PICTURE
    # -------------------------------
    s3_key = upload_profile_picture(file=file)

    profile.profile_picture = s3_key
    db.commit()

    return {
        "message": "Profile picture replaced successfully",
        "s3_key": s3_key
    }



@router.get("/education")
def list_education(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)
    user = db.query(User).filter(User.cognito_sub == payload["sub"]).first()

    if not user or not user.candidate_profile:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return user.candidate_profile.educations

@router.post("/education")
def add_education(
    data: CandidateEducationCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    # 1️⃣ Decode token
    payload = decode_cognito_token(token)
    sub = payload["sub"]

    # 2️⃣ Fetch user
    user = db.query(User).filter(User.cognito_sub == sub).first()
    if not user or user.role != UserRole.user:
        raise HTTPException(status_code=403, detail="Not a candidate")

    # 3️⃣ Fetch candidate profile
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 4️⃣ Create education record
    education = CandidateEducation(
        candidate_id=profile.id,
        institution=data.institution,
        degree=data.degree,
        field_of_study=data.field_of_study,
        start_year=data.start_year,
        end_year=data.end_year,
        grade=data.grade,
    )

    db.add(education)
    db.commit()

    return {"message": "Education added successfully"}


@router.get("/experience")
def list_experience(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)
    user = db.query(User).filter(User.cognito_sub == payload["sub"]).first()

    if not user or not user.candidate_profile:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return user.candidate_profile.experiences

@router.post("/experience")
def add_experience(
    data: CandidateExperienceCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    # 1️⃣ Decode token
    payload = decode_cognito_token(token)
    sub = payload["sub"]

    # 2️⃣ Fetch user
    user = db.query(User).filter(User.cognito_sub == sub).first()
    if not user or user.role != UserRole.user:
        raise HTTPException(status_code=403, detail="Not a candidate")

    # 3️⃣ Fetch candidate profile
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 4️⃣ Create experience
    experience = CandidateExperience(
        candidate_id=profile.id,
        company_name=data.company_name,
        role=data.role,
        start_date=data.start_date,
        end_date=data.end_date,
        is_current=data.is_current,
        description=data.description,
    )

    db.add(experience)
    db.commit()

    return {"message": "Experience added successfully"}

#skills

@router.post("/skills")
def add_skill(
    data: CandidateSkillCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)
    sub = payload["sub"]

    user = db.query(User).filter(User.cognito_sub == sub).first()
    if not user or user.role != UserRole.user:
        raise HTTPException(status_code=403, detail="Not a candidate")

    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Validate skill
    skill = db.query(Skill).filter(Skill.id == data.skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Prevent duplicate
    exists = db.query(CandidateSkill).filter(
        CandidateSkill.candidate_id == profile.id,
        CandidateSkill.skill_id == data.skill_id,
    ).first()

    if exists:
        raise HTTPException(status_code=400, detail="Skill already added")

    candidate_skill = CandidateSkill(
        candidate_id=profile.id,
        skill_id=data.skill_id,
        proficiency=data.proficiency,
        years_of_experience=data.years_of_experience,
    )

    db.add(candidate_skill)
    db.commit()

    return {"message": "Skill added successfully"}

@router.get("/skills", response_model=list[CandidateSkillRead])
def list_skills(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)
    user = db.query(User).filter(User.cognito_sub == payload["sub"]).first()

    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.id
    ).first()

    return profile.skills

@router.get("/projects")
def list_projects(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)
    user = db.query(User).filter(User.cognito_sub == payload["sub"]).first()

    if not user or not user.candidate_profile:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return user.candidate_profile.projects


@router.post("/projects")
def add_project(
    data: CandidateProjectCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)
    sub = payload["sub"]

    user = db.query(User).filter(User.cognito_sub == sub).first()
    if not user or user.role != UserRole.user:
        raise HTTPException(status_code=403, detail="Not a candidate")

    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    project = CandidateProject(
        candidate_id=profile.id,
        title=data.title,
        description=data.description,
        technologies_used=data.technologies_used,
        project_url=data.project_url,
        start_date=data.start_date,
        end_date=data.end_date,
    )

    db.add(project)
    db.commit()

    return {"message": "Project added successfully"}
@router.delete("/projects/{project_id}")
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)
    sub = payload["sub"]

    user = db.query(User).filter(User.cognito_sub == sub).first()
    if not user or not user.candidate_profile:
        raise HTTPException(status_code=404, detail="Candidate not found")

    project = (
        db.query(CandidateProject)
        .filter(
            CandidateProject.id == project_id,
            CandidateProject.candidate_id == user.candidate_profile.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    return {"message": "Project deleted successfully"}



def calculate_profile_completion(profile: CandidateProfile):
    score = 0
    missing = []

    # 1️⃣ Basic profile – 40%
    if (
        profile.current_location
        and profile.total_experience is not None
        and profile.profile_summary
    ):
        score += 40
    else:
        missing.append("Complete basic profile")

    # 2️⃣ Education – 20%
    if profile.educations and len(profile.educations) > 0:
        score += 20
    else:
        missing.append("Add education")

    # 3️⃣ Experience – 25%
    if profile.experiences and len(profile.experiences) > 0:
        score += 25
    else:
        missing.append("Add experience")

    # 4️⃣ Skills – 15%
    if profile.skills and len(profile.skills) > 0:
        score += 15
    else:
        missing.append("Add skills")

    return {
        "percentage": min(score, 100),
        "missing_sections": missing,
    }


@router.get("/profile-completion")
def profile_completion(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    # 1️⃣ Decode token
    payload = decode_cognito_token(token)
    sub = payload["sub"]

    # 2️⃣ Fetch user
    user = db.query(User).filter(User.cognito_sub == sub).first()
    if not user or user.role != UserRole.user:
        raise HTTPException(status_code=403, detail="Not a candidate")

    # 3️⃣ Fetch candidate profile
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 4️⃣ Calculate completion
    return calculate_profile_completion(profile)

