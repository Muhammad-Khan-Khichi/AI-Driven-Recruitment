import json
import os
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db, User, Resume, JobSearch, Application   
from .auth import get_current_user
from agent.resume_agent import run_job_search
from agent.filter_tools import filter_jobs

# ✅ ONLY ONE ROUTER
router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


# ─── Request Models ───────────────────────────────────────
class JobSearchRequest(BaseModel):
    location: Optional[str] = None
    generate_cover_letters: bool = False


class ApplicationRequest(BaseModel):
    job_title: str
    company: str
    job_url: str
    cover_letter: Optional[str] = None
    status: str = "pending"
    notes: Optional[str] = None


class FilterRequest(BaseModel):
    jobs: List[dict]
    remote_only: Optional[bool] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    days_ago: Optional[int] = None
    experience_level: Optional[str] = None
    company_blacklist: Optional[List[str]] = None
    keywords_required: Optional[List[str]] = None
    keywords_excluded: Optional[List[str]] = None


# ─── Resume Upload ────────────────────────────────────────
@router.post("/upload-resume")
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and parse resume PDF."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    upload_dir = "data/resumes"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"user_{current_user.id}_{file.filename}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    from tools.resume_tools import load_resume_text, extract_skills_from_resume
    text = load_resume_text(file_path)
    profile = extract_skills_from_resume(text)

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        parsed_text=text[:5000],
        extracted_skills=json.dumps(profile.get("skills", [])),
        extracted_roles=json.dumps(profile.get("job_titles", []))
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "resume_id": resume.id,
        "filename": file.filename,
        "skills": profile.get("skills", []),
        "roles": profile.get("job_titles", []),
        "parsed_chars": len(text)
    }


# ─── Job Search (POST) ────────────────────────────────────
@router.post("/search")
def search_jobs(
    request: JobSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run job search agent."""
    resume = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.uploaded_at.desc()).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    # Find the search_jobs endpoint and update:
    results = run_job_search(
        resume_path=resume.file_path,
        user_name=current_user.full_name or current_user.username,
        generate_cover_letters=request.generate_cover_letters,
        location=request.location or current_user.location,
        user_id=current_user.id  # Pass user_id for resume vector storage
    )

    search = JobSearch(
        user_id=current_user.id,
        resume_id=resume.id,
        location=request.location or current_user.location,
        jobs_found=json.dumps(results.get("all_jobs", [])),
        top_matches=json.dumps(results.get("top_jobs", []))
    )
    db.add(search)
    db.commit()

    return results


# ─── Search History ───────────────────────────────────────
@router.get("/history")
def get_search_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all past searches."""
    searches = db.query(JobSearch).filter(JobSearch.user_id == current_user.id).order_by(JobSearch.created_at.desc()).limit(20).all()

    return [
        {
            "id": s.id,
            "location": s.location,
            "created_at": s.created_at.isoformat(),
            "jobs_count": len(json.loads(s.jobs_found)) if s.jobs_found else 0,
            "top_matches_count": len(json.loads(s.top_matches)) if s.top_matches else 0
        }
        for s in searches
    ]


# ─── Applications ─────────────────────────────────────────
@router.post("/applications")
def track_application(
    request: ApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track a job application."""
    app = Application(
        user_id=current_user.id,
        job_title=request.job_title,
        company=request.company,
        job_url=request.job_url,
        cover_letter=request.cover_letter,
        status=request.status,
        notes=request.notes
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    return {
        "id": app.id,
        "status": app.status,
        "created_at": app.applied_at.isoformat()
    }


@router.get("/applications")
def list_applications(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's tracked applications."""
    query = db.query(Application).filter(Application.user_id == current_user.id)
    if status:
        query = query.filter(Application.status == status)

    apps = query.order_by(Application.applied_at.desc()).all()
    return [
        {
            "id": a.id,
            "job_title": a.job_title,
            "company": a.company,
            "job_url": a.job_url,
            "status": a.status,
            "notes": a.notes,
            "applied_at": a.applied_at.isoformat()
        }
        for a in apps
    ]


@router.patch("/applications/{app_id}")
def update_application(
    app_id: int,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update application status."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if status:
        app.status = status
    if notes:
        app.notes = notes

    db.commit()
    return {"id": app.id, "status": app.status, "notes": app.notes}


# ─── Smart Filtering ──────────────────────────────────────
@router.post("/filter")
async def filter_jobs_endpoint(req: FilterRequest):
    """Apply smart filters to a list of jobs."""
    try:
        filtered = filter_jobs(
            jobs=req.jobs,
            remote_only=req.remote_only,
            min_salary=req.min_salary,
            max_salary=req.max_salary,
            days_ago=req.days_ago,
            experience_level=req.experience_level,
            company_blacklist=req.company_blacklist,
            keywords_required=req.keywords_required,
            keywords_excluded=req.keywords_excluded
        )

        return {
            "total_before": len(req.jobs),
            "total_after": len(filtered),
            "filtered_count": len(req.jobs) - len(filtered),
            "jobs": filtered
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filter error: {str(e)}")