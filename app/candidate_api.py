from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, status
from sqlalchemy import func, and_,text
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import List, Optional
from .db import get_db
from .utils.s3 import upload_profile_picture, upload_resume as upload_resume_s3, delete_file, generate_presigned_url 
from .models import (
    User,
    CandidateProfile,
    UserRole,
    CandidateEducation,
    CandidateExperience,
    CandidateSkill,
    Skill,
    Job,
    CandidateProject,
    ProfileView,
    Resume,
    Application,
    SavedJob,
)
from .schemas import (
    CandidateProfileCreate,
    CandidateProfileRead,
    CandidateEducationCreate,
    CandidateEducationRead,
    CandidateExperienceCreate,
    CandidateExperienceRead,
    CandidateSkillRead,
    CandidateSkillInput,
    CandidateProjectCreate,
    CandidateProjectRead,
    ResumeRead,
    ProfileAnalytics,
    ProfileCompletion,
    CandidateProfileUpdate
)


from .auth_api import get_current_candidate, get_current_recruiter,oauth2_scheme,decode_cognito_token
router = APIRouter(prefix="/candidate", tags=["Candidate"])


# =====================================================
# DEPENDENCIES & HELPERS
# =====================================================
def get_candidate_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_candidate)
) -> CandidateProfile:

    profile = db.query(CandidateProfile).options(
        joinedload(CandidateProfile.user),
        joinedload(CandidateProfile.educations),
        joinedload(CandidateProfile.experiences),
        joinedload(CandidateProfile.skills).joinedload(CandidateSkill.skill),
        joinedload(CandidateProfile.projects),
        joinedload(CandidateProfile.resumes),
    ).filter(
        CandidateProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    # ✅ GUARANTEE public_username FOR ALL
    if not profile.public_username:
        base = profile.user.full_name.lower().replace(" ", "")
        candidate_username = base
        counter = 1

        while db.query(CandidateProfile).filter(
            CandidateProfile.public_username == candidate_username
        ).first():
            candidate_username = f"{base}{counter}"
            counter += 1

        profile.public_username = candidate_username
        db.commit()
        db.refresh(profile)

    return profile


# =====================================================
# PROFILE MANAGEMENT
# =====================================================

@router.get(
    "/profile",
    response_model=CandidateProfileRead,
)
def get_profile(
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    user = profile.user

    return {
        "id": profile.id,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "profile_picture": profile.profile_picture,
        "current_location": profile.current_location,
        "preferred_location": profile.preferred_location,
        "total_experience": profile.total_experience,
        "current_ctc": profile.current_ctc,
        "expected_ctc": profile.expected_ctc,
        "profile_summary": profile.profile_summary,
        "resume_headline": profile.resume_headline,
        "notice_period": profile.notice_period,
        "willing_to_relocate": profile.willing_to_relocate,
        "preferred_shift": profile.preferred_shift,
        "employment_type_preference": profile.employment_type_preference,
        "visibility": profile.visibility,
        "linkedin_url": profile.linkedin_url,
        "github_url": profile.github_url,
        "portfolio_url": profile.portfolio_url,
        "public_username": profile.public_username, 
        "last_active": profile.last_active,
        "is_active": profile.is_active,
        "created_at": profile.created_at,
    }


@router.put(
    "/profile",
    response_model=CandidateProfileRead,
)
def update_profile(
    payload: CandidateProfileUpdate,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    try:
        ALLOWED_FIELDS = {
            "current_location",
            "preferred_location",
            "total_experience",
            "current_ctc",
            "expected_ctc",
            "profile_summary",
            "resume_headline",
            "notice_period",
            "willing_to_relocate",
            "preferred_shift",
            "employment_type_preference",
            "visibility",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "public_username",
        }

        update_data = payload.model_dump(exclude_unset=True)
        user = profile.user
        if "phone_number" in update_data:
            user.phone_number = update_data.pop("phone_number")
        if "public_username" in update_data:
            existing = db.query(CandidateProfile).filter(
                func.lower(CandidateProfile.public_username) == update_data["public_username"].lower(),
                CandidateProfile.id != profile.id
            ).first()

            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Public username already taken"
                )
        for key, value in update_data.items():
            if key in ALLOWED_FIELDS:
                setattr(profile, key, value)

        profile.last_active = func.now()
        # 🔗 AUTO-GENERATE USERNAME IF NOT SET
        if not profile.public_username:
            base = profile.user.full_name.lower().replace(" ", "")
            candidate_username = base

            counter = 1
            while db.query(CandidateProfile).filter(
                CandidateProfile.public_username == candidate_username
            ).first():
                candidate_username = f"{base}{counter}"
                counter += 1

            profile.public_username = candidate_username

        db.commit()
        db.refresh(profile)

        return {
            "id": profile.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "profile_picture": profile.profile_picture,
            "current_location": profile.current_location,
            "preferred_location": profile.preferred_location,
            "total_experience": profile.total_experience,
            "current_ctc": profile.current_ctc,
            "expected_ctc": profile.expected_ctc,
            "profile_summary": profile.profile_summary,
            "resume_headline": profile.resume_headline,
            "notice_period": profile.notice_period,
            "willing_to_relocate": profile.willing_to_relocate,
            "preferred_shift": profile.preferred_shift,
            "employment_type_preference": profile.employment_type_preference,
            "visibility": profile.visibility,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
            "portfolio_url": profile.portfolio_url,
            "public_username": profile.public_username, 
            "last_active": profile.last_active,
            "is_active": profile.is_active,
            "created_at": profile.created_at,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )

@router.post(
    "/profile-picture",
    summary="Upload or replace profile picture"
)
def upload_profile_picture_api(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile),
):
    # =================================================
    # HARD VALIDATION (FIXES NoneType CRASH)
    # =================================================
    if file is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file name")

    if not file.content_type:
        raise HTTPException(status_code=400, detail="Invalid file type")

    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/jpg"}
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG or PNG allowed")

    # =================================================
    # FILE SIZE CHECK (SAFE)
    # =================================================
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size <= 0:
        raise HTTPException(status_code=400, detail="Empty file")

    if size > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Max size is 2MB")

    try:
        # =================================================
        # DELETE OLD PICTURE (IF EXISTS)
        # =================================================
        if profile.profile_picture:
            delete_file(profile.profile_picture)

        # =================================================
        # UPLOAD NEW PICTURE
        # =================================================
        s3_key = upload_profile_picture(file)

        profile.profile_picture = s3_key
        db.commit()

        return {
            "message": "Profile picture uploaded successfully",
            "s3_key": s3_key,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload profile picture: {str(e)}"
        )




# =====================================================
# EDUCATION - FULL CRUD
# =====================================================

@router.get(
    "/education",
    response_model=List[CandidateEducationRead],
    summary="Get education history",
    description="Retrieve all education records for the candidate"
)
def list_education(
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Get all education records."""
    return profile.educations


@router.post(
    "/education",
    status_code=status.HTTP_201_CREATED,
    summary="Add education",
    description="Add a new education record"
)
def add_education(
    data: CandidateEducationCreate,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Add education record."""
    try:
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
        db.refresh(education)
        
        return {
            "message": "Education added successfully",
            "id": education.id,
            "education": education
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add education: {str(e)}"
        )


@router.put(
    "/education/{edu_id}",
    summary="Update education",
    description="Update an existing education record"
)
def update_education(
    edu_id: UUID,
    data: CandidateEducationCreate,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Update education record."""
    education = db.query(CandidateEducation).filter(
        and_(
            CandidateEducation.id == edu_id,
            CandidateEducation.candidate_id == profile.id
        )
    ).first()
    
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found"
        )
    
    try:
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(education, key, value)
        
        db.commit()
        
        return {
            "message": "Education updated successfully",
            "id": education.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update education: {str(e)}"
        )


@router.delete(
    "/education/{edu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete education",
    description="Delete an education record"
)
def delete_education(
    edu_id: UUID,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Delete education record."""
    education = db.query(CandidateEducation).filter(
        and_(
            CandidateEducation.id == edu_id,
            CandidateEducation.candidate_id == profile.id
        )
    ).first()
    
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found"
        )
    
    try:
        db.delete(education)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete education: {str(e)}"
        )


# =====================================================
# EXPERIENCE - FULL CRUD
# =====================================================

@router.get(
    "/experience",
    response_model=List[CandidateExperienceRead],
    summary="Get work experience",
    description="Retrieve all work experience records"
)
def list_experience(
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Get all experience records."""
    return profile.experiences


@router.post(
    "/experience",
    status_code=status.HTTP_201_CREATED,
    summary="Add experience",
    description="Add a new work experience record"
)
def add_experience(
    data: CandidateExperienceCreate,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Add experience record."""
    try:
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
        db.refresh(experience)
        
        return {
            "message": "Experience added successfully",
            "id": experience.id,
            "experience": experience
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add experience: {str(e)}"
        )


@router.put(
    "/experience/{exp_id}",
    summary="Update experience",
    description="Update an existing work experience record"
)
def update_experience(
    exp_id: UUID,
    data: CandidateExperienceCreate,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Update experience record."""
    experience = db.query(CandidateExperience).filter(
        and_(
            CandidateExperience.id == exp_id,
            CandidateExperience.candidate_id == profile.id
        )
    ).first()
    
    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience record not found"
        )
    
    try:
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(experience, key, value)
        
        db.commit()
        
        return {
            "message": "Experience updated successfully",
            "id": experience.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update experience: {str(e)}"
        )


@router.delete(
    "/experience/{exp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete experience",
    description="Delete a work experience record"
)
def delete_experience(
    exp_id: UUID,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Delete experience record."""
    experience = db.query(CandidateExperience).filter(
        and_(
            CandidateExperience.id == exp_id,
            CandidateExperience.candidate_id == profile.id
        )
    ).first()
    
    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience record not found"
        )
    
    try:
        db.delete(experience)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete experience: {str(e)}"
        )


# =====================================================
# SKILLS MANAGEMENT
# =====================================================

@router.get("/skills")
def list_skills(
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    skills = (
        db.query(CandidateSkill)
        .options(joinedload(CandidateSkill.skill))
        .filter(CandidateSkill.candidate_id == profile.id)
        .all()
    )

    return [
        {
            "skill": {
                "id": cs.skill.id,
                "name": cs.skill.name
            },
            "proficiency": cs.proficiency,
            "years_of_experience": cs.years_of_experience
        }
        for cs in skills
    ]

@router.put(
    "/skills",
    summary="Update skills",
    description="Replace all skills with new list (upsert operation)"
)
def upsert_skills(
    skills: List[CandidateSkillInput] = Body(...),
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Replace all skills with new list."""
    if skills is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skills payload missing"
        )
    
    try:
        # Delete existing skills
        db.query(CandidateSkill).filter(
            CandidateSkill.candidate_id == profile.id
        ).delete(synchronize_session=False)
        
        seen = set()
        
        for skill_input in skills:
            normalized_name = skill_input.name.strip().lower()
            
            if not normalized_name:
                continue
            
            if normalized_name in seen:
                continue
            seen.add(normalized_name)
            
            # Find or create skill
            skill = db.query(Skill).filter(
                func.lower(Skill.name) == normalized_name
            ).first()
            
            if not skill:
                skill = Skill(name=skill_input.name.strip().title())
                db.add(skill)
                db.flush()
            
            # Create candidate skill association
            candidate_skill = CandidateSkill(
                candidate_id=profile.id,
                skill_id=skill.id,
                proficiency=skill_input.proficiency,
                years_of_experience=skill_input.years_of_experience,
            )
            
            db.add(candidate_skill)
        
        db.commit()
        
        # Get updated skills
        updated_skills = db.query(CandidateSkill).filter(
            CandidateSkill.candidate_id == profile.id
        ).options(joinedload(CandidateSkill.skill)).all()
        
        return {
            "message": f"{len(seen)} skills updated successfully",
            "skills_count": len(seen),
            "skills": [
                {
                    "skill": {
                        "name": cs.skill.name,
                        "id": cs.skill.id
                    },
                    "proficiency": cs.proficiency,
                    "years_of_experience": cs.years_of_experience
                }
                for cs in updated_skills
            ]
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update skills: {str(e)}"
        )


# =====================================================
# PROJECTS - FULL CRUD
# =====================================================

@router.get(
    "/projects",
    response_model=List[CandidateProjectRead],
    summary="Get projects",
    description="Retrieve all projects"
)
def list_projects(
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Get all projects."""
    return profile.projects


@router.post(
    "/projects",
    status_code=status.HTTP_201_CREATED,
    summary="Add project",
    description="Add a new project"
)
def add_project(
    data: CandidateProjectCreate,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Add project."""
    try:
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
        db.refresh(project)
        
        return {
            "message": "Project added successfully",
            "id": project.id,
            "project": project
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add project: {str(e)}"
        )


@router.put(
    "/projects/{project_id}",
    summary="Update project",
    description="Update an existing project"
)
def update_project(
    project_id: UUID,
    data: CandidateProjectCreate,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Update project."""
    project = db.query(CandidateProject).filter(
        and_(
            CandidateProject.id == project_id,
            CandidateProject.candidate_id == profile.id
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    try:
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)
        
        db.commit()
        
        return {
            "message": "Project updated successfully",
            "id": project.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Delete a project"
)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Delete project."""
    project = db.query(CandidateProject).filter(
        and_(
            CandidateProject.id == project_id,
            CandidateProject.candidate_id == profile.id
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    try:
        db.delete(project)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


# =====================================================
# RESUME MANAGEMENT
# =====================================================

@router.post("/resume/upload", summary="Upload resume")
def upload_resume(
    file: UploadFile = File(...),
    is_primary: bool = True,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile),
):
    ALLOWED_TYPES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")

    MAX_SIZE = 5 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    try:
        # 1️⃣ Mark existing primary false
        if is_primary:
            db.query(Resume).filter(
                Resume.candidate_id == profile.id,
                Resume.is_primary == True
            ).update({"is_primary": False})
            db.flush()

        # 2️⃣ Create DB record FIRST
        resume = Resume(
            candidate_id=profile.id,
            resume_s3_key="PENDING",
            original_filename=file.filename,
            content_type=file.content_type,
            file_size=file_size,
            is_primary=is_primary,
        )
        db.add(resume)
        db.flush()  # get resume.id

        # 3️⃣ Upload to S3
        s3_key = upload_resume_s3(file=file)

        # 4️⃣ Update real key
        resume.resume_s3_key = s3_key
        db.commit()
        db.refresh(resume)

        return {
            "message": "Resume uploaded successfully",
            "resume_id": resume.id,
            "s3_key": s3_key,
            "file_name": file.filename,
            "is_primary": is_primary,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



@router.get(
    "/resume/list",
    response_model=List[ResumeRead],
    summary="List resumes",
    description="Get all uploaded resumes"
)
def list_resumes(
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """List all resumes."""
    return profile.resumes


@router.delete(
    "/resume/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete resume",
    description="Delete a resume file"
)
def delete_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Delete resume."""
    resume = db.query(Resume).filter(
        and_(
            Resume.id == resume_id,
            Resume.candidate_id == profile.id
        )
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    try:
        # Delete from S3
        try:
            delete_file(resume.resume_s3_key)
        except Exception:
            pass
        
        # Delete from database
        db.delete(resume)
        
        # If this was primary, mark another resume as primary if available
        if resume.is_primary:
            other_resume = db.query(Resume).filter(
                and_(
                    Resume.candidate_id == profile.id,
                    Resume.id != resume_id
                )
            ).first()
            
            if other_resume:
                other_resume.is_primary = True
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resume: {str(e)}"
        )


# =====================================================
# PROFILE COMPLETION
# =====================================================
def calculate_profile_completion(profile: CandidateProfile) -> dict:
    score = 0
    missing = []
    suggestions = []

    # ---------------- BASIC PROFILE (20)
    basic_fields = [
        profile.current_location,
        profile.profile_summary,
        profile.resume_headline,
    ]
    if all(basic_fields):
        score += 20
    else:
        missing.append("Basic profile details")
        suggestions.append("Complete location, summary, and resume headline")

    # ---------------- EDUCATION (10)
    if profile.educations:
        score += 10
    else:
        missing.append("Education")
        suggestions.append("Add at least one education record")

    # ---------------- EXPERIENCE OR FRESHER PROJECTS (20)
    if profile.experiences:
        score += 20
    elif profile.projects:
        score += 20
        suggestions.append("Add work experience when available")
    else:
        missing.append("Experience / Projects")
        suggestions.append("Add experience or at least one project")

    # ---------------- SKILLS (15)
    skill_count = len(profile.skills or [])
    if skill_count >= 3:
        score += 15
    elif skill_count > 0:
        score += 10
        suggestions.append("Add at least 3 skills")
    else:
        missing.append("Skills")
        suggestions.append("Add skills to your profile")

    # ---------------- PROJECTS (15)
    if profile.projects:
        score += 15
    else:
        missing.append("Projects")
        suggestions.append("Add projects to showcase your work")

    # ---------------- RESUME (10)
    if profile.resumes:
        score += 10
    else:
        missing.append("Resume")
        suggestions.append("Upload your resume")

    # ---------------- PROFILE PICTURE (5)
    if profile.profile_picture:
        score += 10
    else:
        suggestions.append("Add a professional profile photo")



    return {
        "percentage": score,  # already max 100
        "missing_sections": missing,
        "suggestions": suggestions[:5],
        "is_complete": score == 100,
        "score_breakdown": {
            "basic": 20,
            "education": 10,
            "experience": 20,
            "skills": 15,
            "projects": 15,
            "resume": 10,
            "profile_picture": 10,  # shifted weight
        },
    }




@router.get(
    "/profile-completion",
    response_model=ProfileCompletion,
    summary="Get profile completion",
    description="Calculate profile completion percentage and get suggestions"
)
def profile_completion(
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Calculate and return profile completion metrics."""
    return calculate_profile_completion(profile)


# =====================================================
# ANALYTICS
# =====================================================

@router.get(
    "/profile-analytics",
    response_model=ProfileAnalytics,
    summary="Get profile analytics",
    description="Get comprehensive analytics for the candidate profile"
)
def get_profile_analytics(
    db: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_candidate_profile)
):
    """Get profile analytics."""
    try:
        # Profile views
        total_views = db.query(ProfileView).filter(
            ProfileView.candidate_id == profile.id
        ).count()
        
        # Recent views (last 30 days)
        recent_views = db.query(func.count(ProfileView.id)).filter(
            and_(
                ProfileView.candidate_id == profile.id,
                ProfileView.viewed_at >= func.now() - text("INTERVAL '30 days'")
            )
        ).scalar() or 0
        
        # Applications
        total_applications = db.query(Application).filter(
            Application.candidate_id == profile.id
        ).count()
        
        # Application status breakdown
        application_stats = db.query(
            Application.status,
            func.count(Application.id)
        ).filter(
            Application.candidate_id == profile.id
        ).group_by(Application.status).all()
        
        # Saved jobs
        saved_jobs_count = db.query(SavedJob).filter(
            SavedJob.candidate_id == profile.id
        ).count()
        
        # Profile completion
        completion_data = calculate_profile_completion(profile)
        
        return ProfileAnalytics(
            profile_views=total_views,
            recent_views=recent_views,
            total_applications=total_applications,
            saved_jobs=saved_jobs_count,
            application_breakdown={
                (status.value if hasattr(status, "value") else str(status)): count
                for status, count in application_stats
            },
            profile_completion=completion_data["percentage"],
            profile_score=completion_data["percentage"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analytics: {str(e)}"
        )
    




@router.get(
    "/public/{username}",
    summary="Public candidate profile (LinkedIn style)"
)
def public_profile(
    username: str,
    db: Session = Depends(get_db)
):
    profile = (
        db.query(CandidateProfile)
        .options(
            joinedload(CandidateProfile.user),
            joinedload(CandidateProfile.educations),
            joinedload(CandidateProfile.experiences),
            joinedload(CandidateProfile.skills).joinedload(CandidateSkill.skill),
            joinedload(CandidateProfile.projects),
        )
        .filter(
            CandidateProfile.public_username == username,
            CandidateProfile.visibility == "public"
        )
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "full_name": profile.user.full_name,
        "email": profile.user.email,              # ✅ ADD THIS
        "headline": profile.resume_headline,
        "summary": profile.profile_summary,
        "experience_years": profile.total_experience,
        "location": profile.current_location,
        "phone_number": profile.user.phone_number,
        "experience": profile.experiences,
        "education": profile.educations,
        "skills": [
            {
                "name": cs.skill.name,
                "proficiency": cs.proficiency
            }
            for cs in profile.skills
        ],
        "projects": profile.projects,
        "profile_picture": profile.profile_picture,
    }



@router.get(
    "/username-available/{username}",
    summary="Check if public username is available"
)
def check_username_availability(
    username: str,
    db: Session = Depends(get_db)
):
    existing = db.query(CandidateProfile).filter(
        func.lower(CandidateProfile.public_username) == username.lower()
    ).first()

    return {
        "username": username,
        "available": existing is None
    }
# =====================================================
# RECRUITER – VIEW CANDIDATE PROFILE (TEAM SAFE)
# =====================================================
@router.get("/candidate/{candidate_id}")
def get_candidate_profile_for_recruiter(
    candidate_id: UUID,
    application_id: UUID,   # ✅ REQUIRED
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    # ---------------- AUTH ----------------
    payload = decode_cognito_token(token)

    recruiter = (
        db.query(User)
        .filter(
            User.cognito_sub == payload["sub"],
            User.role == UserRole.recruiter,
        )
        .first()
    )

    if not recruiter:
        raise HTTPException(403, "Recruiter only")

    # ---------------- FETCH CANDIDATE ----------------
    candidate = (
        db.query(CandidateProfile)
        .options(
            joinedload(CandidateProfile.user),
            joinedload(CandidateProfile.educations),
            joinedload(CandidateProfile.experiences),
            joinedload(CandidateProfile.projects),
            joinedload(CandidateProfile.skills).joinedload(CandidateSkill.skill),
        )
        .filter(CandidateProfile.id == candidate_id)
        .first()
    )

    if not candidate:
        raise HTTPException(404, "Candidate not found")

    # ---------------- FETCH APPLICATION + RESUME ----------------

    view = ProfileView(
        candidate_id=candidate.id,
    )
    db.add(view)
    db.commit()
    application = (
        db.query(Application)
        .join(Resume)
        .filter(
            Application.id == application_id,
            Application.candidate_id == candidate.id,
        )
        .first()
    )

    resume = None
    if application and application.resume:
        resume = {
            "resume_id": application.resume.id,
            "filename": application.resume.original_filename,
        }

    return {
        "candidate": {
            "id": candidate.id,
            "profile_picture": candidate.profile_picture,
            "full_name": candidate.user.full_name,
            "email": candidate.user.email,
            "phone": candidate.user.phone_number,
            "location": candidate.current_location,
            
            "profile_summary": candidate.profile_summary,
            "total_experience": candidate.total_experience,
            "notice_period": candidate.notice_period,
        },

        "skills": [
            {
                "name": cs.skill.name,
                "proficiency": cs.proficiency,
            }
            for cs in candidate.skills
        ],

        "education": [
            {
                "institution": e.institution,
                "degree": e.degree,
                "field": e.field_of_study,
                "start_year": e.start_year,
                "end_year": e.end_year,
            }
            for e in candidate.educations
        ],

        "experience": [
            {
                "company": exp.company_name,
                "role": exp.role,
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "description": exp.description,
            }
            for exp in candidate.experiences
        ],

        "projects": [
            {
                "title": p.title,
                "description": p.description,
                "technologies": p.technologies_used,
            }
            for p in candidate.projects
        ],

        # ✅ CORRECT PLACE
        "resume": resume,
    }

    
    
    
@router.get("/resume/access/application/{application_id}")
def access_application_resume(
    application_id: UUID,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_cognito_token(token)

    recruiter = (
        db.query(User)
        .filter(
            User.cognito_sub == payload["sub"],
            User.role == UserRole.recruiter,
        )
        .first()
    )

    if not recruiter:
        raise HTTPException(403, "Recruiter only")

    application = (
        db.query(Application)
        .join(Resume)
        .filter(Application.id == application_id)
        .first()
    )

    if not application:
        raise HTTPException(404, "Application not found")

    resume = application.resume

    # generate signed url (example)
    if not resume or not resume.resume_s3_key:
        raise HTTPException(404, "Resume file not found")

    url = generate_presigned_url(resume.resume_s3_key)

    return {
        "resume_id": resume.id,
        "filename": resume.original_filename,
        "url": url,
    }

@router.get("/media/profile-picture/{s3_key:path}")
def access_profile_picture_for_recruiter(
    s3_key: str,
    application_id: UUID,
    db: Session = Depends(get_db),
    recruiter=Depends(get_current_recruiter),
):
    application = (
        db.query(Application)
        .join(CandidateProfile)
        .filter(
            Application.id == application_id,
            CandidateProfile.profile_picture == s3_key,
        )
        .first()
    )

    if not application:
        raise HTTPException(403, "Not authorized to view this image")

    url = generate_presigned_url(s3_key)
    return {"url": url}

@router.get("/resume/access/application/{application_id}")
def access_resume_for_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    recruiter=Depends(get_current_recruiter),
):
    application = (
        db.query(Application)
        .join(Resume)
        .filter(Application.id == application_id)
        .first()
    )

    if not application or not application.resume:
        raise HTTPException(404, "Resume not found")

    url = generate_presigned_url(application.resume.resume_s3_key)

    # optional analytics
    application.resume.downloaded_count += 1
    db.commit()

    return {"url": url}
