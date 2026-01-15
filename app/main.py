from fastapi import FastAPI
from dotenv import load_dotenv
from app.db import engine
from app import models
from app.signup_api import router as signup_router
from app.jobs_api import router as jobs_router

load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Recruitment Portal API")

app.include_router(jobs_router)





