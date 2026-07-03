from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .routes_auth import router as auth_router
from .routes_jobs import router as jobs_router
from api.admin import router as admin_router
from api.routes_semantic import router as semantic_router
from api.routes_resume import router as resume_router
from api.routes_linkedin import router as linkedin_router
from api.routes_interview import router as interview_router
from api.routes_oauth import router as oauth_router
from api import cover_letter
from api import password_reset



app = FastAPI(
    title="Job-Searcher AI Agent API",
    description="AI-powered job search with FastAPI",
    version="1.0.0"
)

app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-change-this-to-something-random-and-secure"  # Change this!
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8501", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(admin_router)
app.include_router(semantic_router)
app.include_router(resume_router)
app.include_router(linkedin_router)
app.include_router(interview_router)
app.include_router(oauth_router)
app.include_router(cover_letter.router)
app.include_router(password_reset.router) 



@app.get("/")
def root():
    return {
        "app": "Job-Searcher AI Agent",
        "version": "1.0.0",
        "features": [
            "auth", "job-search", "smart-filters",
            "semantic-search", "cover-letters", "resume-optimization",
            "linkedin-optimization", "interview-prep"
        ],
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}