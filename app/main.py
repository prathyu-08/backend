from fastapi import FastAPI
from dotenv import load_dotenv
from .interview_api import router as interview_router
from .interviewer_api import router as interviewer_router
from .notification_api import router as notification_router
from .db import engine
from . import models
from .admin_api import router as admin_router

from .auth_api import router as auth_router
from .jobs_api import router as jobs_router
from .candidate_api import router as candidate_router
from .application_api import router as application_router

from .resume_api import router as resume_router
from .skills_api import router as skills_router
from .job_descriptions import router as job_descriptions_router
from .job_application_forms_api import router as job_application_forms_router


load_dotenv()

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Recruitment Portal API")

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(candidate_router)
app.include_router(application_router)
app.include_router(interview_router)
app.include_router(interviewer_router)
app.include_router(notification_router)
app.include_router(resume_router)
app.include_router(skills_router)
app.include_router(admin_router)
app.include_router(job_descriptions_router)
app.include_router(job_application_forms_router)
