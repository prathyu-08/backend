router = APIRouter(prefix="/auth", tags=["Auth"])

# ------------------ USER REGISTRATION ------------------
@router.post("/register")
def register_user(data: schemas.UserRegister, db: Session = Depends(get_db)):

    existing_user = db.query(models.User).filter(
        (models.User.username == data.username) |
        (models.User.email == data.email)
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = models.User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        phone_number=data.phone_number,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_verified=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User registered successfully", "user_id": user.id}

# ------------------ HR / RECRUITER REGISTRATION ------------------
@router.post("/register/recruiter")
def register_recruiter(data: schemas.RecruiterRegister, db: Session = Depends(get_db)):

    existing_user = db.query(models.User).filter(
        (models.User.username == data.username) |
        (models.User.email == data.email)
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = models.User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        phone_number=data.phone_number,
        hashed_password=hash_password(data.password),
        role=models.UserRole.recruiter,
        is_verified=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    recruiter = models.Recruiter(
        user_id=user.id,
        company_name=data.company_name,
        company_website=data.company_website,
        company_location=data.company_location,
        designation=data.designation
    )

    db.add(recruiter)
    db.commit()

    return {"message": "Recruiter registered successfully", "user_id": user.id}
