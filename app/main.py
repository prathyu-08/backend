from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta

from app.db import engine, get_db
from app.auth import router as auth_router
from app.security import verify_password
from app.email_utils import send_email
from app import models

# ------------------ APP ------------------
app = FastAPI(title="Recruitment Management Portal")

# Create tables only once at startup
@app.on_event("startup")
def on_startup():
    models.Base.metadata.create_all(bind=engine)

# Include registration routes
app.include_router(auth_router)

# ------------------ JWT CONFIG ------------------
SECRET_KEY = "secret123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ------------------ TOKEN CREATE ------------------
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ------------------ LOGIN (Candidate + HR) ------------------
@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.username == form_data.username
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    token = create_access_token(
        {"sub": user.username, "role": user.role.value}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "expires_in": "1 hour"
    }

# ------------------ CURRENT USER ------------------
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

# ------------------ DASHBOARDS ------------------
@app.get("/user")
def user_dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome {user['sub']} (Candidate)"}

@app.get("/recruiter")
def recruiter_dashboard(user=Depends(get_current_user)):
    if user["role"] != "recruiter":
        raise HTTPException(status_code=403, detail="Access denied")
    return {"message": f"Welcome {user['sub']} (Recruiter)"}

# ------------------ HR SEND EMAIL ------------------
@app.post("/recruiter/send-email")
def recruiter_send_email(
    candidate_email: str,
    subject: str,
    message: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Role check
    if user["role"] != "recruiter":
        raise HTTPException(status_code=403, detail="Only HR can send emails")

    # Send email via Gmail
    send_email(candidate_email, subject, message)

    # Save email log in DB
    recruiter = db.query(models.User).filter(
        models.User.username == user["sub"]
    ).first()

    email_log = models.EmailLog(
        recruiter_id=recruiter.id,
        candidate_email=candidate_email,
        subject=subject,
        message=message
    )

    db.add(email_log)
    db.commit()

    return {"message": "Email sent and stored successfully"}

# ------------------ CANDIDATE VIEW EMAILS ------------------
@app.get("/candidate/emails")
def get_candidate_emails(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "user":
        raise HTTPException(status_code=403, detail="Only candidates allowed")

    emails = db.query(models.EmailLog).filter(
        models.EmailLog.candidate_email == user["sub"]
    ).order_by(models.EmailLog.sent_at.desc()).all()

    return emails

# ------------------ HEALTH CHECK ------------------
@app.get("/")
def home():
    return {"message": "API is running"}
