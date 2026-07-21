import asyncio
import hashlib
import json
import os
import tempfile
import traceback
from functools import partial
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db, User, Resume, JobSearch, Application
from .auth import get_current_user
from agent.resume_agent import run_job_search
from agent.filter_tools import filter_jobs

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


# ============================================================
# Request Models
# ============================================================
class JobSearchRequest(BaseModel):
    location: Optional[str] = None
    generate_cover_letters: bool = False
    time_filter: Optional[str] = "any"


class ResumeJobSearchRequest(BaseModel):
    """Search jobs using resume skills as keywords."""
    resume_id: Optional[int] = None
    location: Optional[str] = None
    max_results_per_keyword: int = 20
    min_match_score: int = 20
    generate_cover_letters: bool = False
    time_filter: Optional[str] = "any"


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


# ============================================================
# Resume Upload (NO PDF SAVED - TEXT ONLY!)
# ============================================================
@router.post("/upload-resume")
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and parse resume PDF. Saves text to DB only.
    If this exact file was already uploaded by this user before,
    skip re-parsing/re-processing and return the existing record."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    content = file.file.read()

    # Compute a hash of the raw file bytes to detect duplicates
    file_hash = hashlib.sha256(content).hexdigest()

    existing = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.file_hash == file_hash
    ).first()

    if existing:
        skills = json.loads(existing.extracted_skills) if existing.extracted_skills else []
        roles = json.loads(existing.extracted_roles) if existing.extracted_roles else []
        return {
            "resume_id": existing.id,
            "filename": existing.filename,
            "skills": skills,
            "roles": roles,
            "parsed_chars": len(existing.parsed_text or ""),
            "message": "",
            "duplicate": True
        }

    suffix = os.path.splitext(file.filename)[1] or ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from tools.resume_tools import load_resume_text, extract_skills_from_resume

        text = load_resume_text(tmp_path)
        profile = extract_skills_from_resume(text)

        resume = Resume(
            user_id=current_user.id,
            filename=file.filename,
            file_path=None,
            file_hash=file_hash,
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
            "parsed_chars": len(text),
            "message": f"  Extracted {len(profile.get('skills', []))} skills (no PDF saved!)",
            "duplicate": False
        }
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
            print(f"🗑️  Deleted temp file: {tmp_path}")


# ============================================================
# Job Search (POST) — uses parsed_text + passes time_filter
# ============================================================
@router.post("/search")
def search_jobs(
    request: JobSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run job search agent."""
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).order_by(Resume.uploaded_at.desc()).first()

    if not resume:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    # Normalize & validate the time_filter
    time_filter = normalize_time_filter(request.time_filter)

    # Debug log so you can verify the location is being used
    print(f'[jobs/search] user_id={current_user.id}, '
          f'location={request.location!r}, time_filter={time_filter!r}')

    results = run_job_search(
        resume_text=resume.parsed_text or "",
        resume_path=resume.file_path,
        user_name=current_user.full_name or current_user.username,
        generate_cover_letters=request.generate_cover_letters,
        location=request.location or current_user.location,
        user_id=current_user.id,
        time_filter=time_filter
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


# ============================================================
# Search History
# ============================================================
@router.get("/history")
def get_search_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all past searches."""
    searches = db.query(JobSearch).filter(
        JobSearch.user_id == current_user.id
    ).order_by(JobSearch.created_at.desc()).limit(20).all()

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


# ============================================================
# Applications
# ============================================================
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


# ============================================================
# Smart Filtering
# ============================================================
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


# ============================================================
# Resume-Based Job Search — ASYNC with thread pool executor
# ============================================================
@router.post("/search-by-resume")
async def search_jobs_by_resume(
    request: ResumeJobSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for jobs using keywords extracted from user's resume.
    
    Uses asyncio.run_in_executor to run the blocking run_job_search() 
    in a thread pool so it doesn't block the FastAPI event loop.
    """
    print(f"🚨 [search-by-resume] STARTED for user_id={current_user.id}")
    
    # Step 1: Get resume
    if request.resume_id:
        resume = db.query(Resume).filter(
            Resume.id == request.resume_id,
            Resume.user_id == current_user.id
        ).first()
    else:
        resume = db.query(Resume).filter(
            Resume.user_id == current_user.id
        ).order_by(Resume.uploaded_at.desc()).first()

    if not resume:
        raise HTTPException(
            status_code=400,
            detail="No resume found. Please upload a resume first."
        )

    # Step 2: Extract skills from resume
    resume_skills = []
    if resume.extracted_skills:
        try:
            skills_data = json.loads(resume.extracted_skills)
            if isinstance(skills_data, list):
                resume_skills = skills_data
            elif isinstance(skills_data, dict):
                resume_skills = skills_data.get("skills", [])
        except (json.JSONDecodeError, TypeError):
            resume_skills = [
                s.strip() for s in resume.extracted_skills.split(",") if s.strip()
            ]

    if not resume_skills:
        raise HTTPException(
            status_code=400,
            detail="Resume has no extracted skills. Please re-upload your resume."
        )

    # Normalize & validate time_filter
    time_filter = normalize_time_filter(request.time_filter)
    print(f'✅ [search-by-resume] Validation done. skills={len(resume_skills)}, '
          f'location={request.location!r}, time_filter={time_filter!r}')

    # Step 3: Generate smart search keywords
    search_keywords = generate_search_keywords(resume_skills)
    print(f"🔍 [search-by-resume] Generated {len(search_keywords)} keywords: {search_keywords[:2]}")

    # Step 4: Run job search for each keyword (in thread pool — non-blocking)
    loop = asyncio.get_event_loop()
    all_jobs = []
    search_results = []

    for keyword in search_keywords[:2]:
        try:
            print(f"🔍 [search-by-resume] Searching for '{keyword}'...")
            
            # Use run_in_executor to run sync run_job_search without blocking
            results = await loop.run_in_executor(
                None,  # default thread pool
                partial(
                    run_job_search,
                    resume_text=resume.parsed_text or "",
                    resume_path=resume.file_path,
                    user_name=current_user.full_name or current_user.username,
                    generate_cover_letters=False,
                    location=request.location or current_user.location,
                    user_id=current_user.id,
                    custom_keywords=[keyword],
                    time_filter=time_filter
                )
            )

            jobs = results.get("all_jobs", [])
            all_jobs.extend(jobs)
            search_results.append({
                "keyword": keyword,
                "jobs_found": len(jobs)
            })
            print(f"✅ [search-by-resume] '{keyword}' returned {len(jobs)} jobs")
            
        except Exception as e:
            print(f"❌ [search-by-resume] Search failed for '{keyword}': {e}")
            traceback.print_exc()
            continue

    # Step 5: Remove duplicates
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        title = (job.get("title") or "").lower().strip()
        company = (job.get("company") or "").lower().strip()
        key = f"{title}|{company}"
        if key not in seen and title:
            seen.add(key)
            unique_jobs.append(job)

    print(f"🔍 [search-by-resume] {len(unique_jobs)} unique jobs after dedup")

    # Step 6: Score each job
    scored_jobs = []
    for job in unique_jobs:
        score, matched, missing = score_job_against_skills(job, resume_skills)

        if score >= request.min_match_score:
            job_copy = dict(job)
            job_copy["match_score"] = score
            job_copy["matched_skills"] = matched
            job_copy["missing_skills"] = missing[:5]
            scored_jobs.append(job_copy)

    # Step 7: Sort by match score
    scored_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    # Step 8: Limit results
    final_jobs = scored_jobs[:request.max_results_per_keyword * 3]

    print(f"✅ [search-by-resume] Returning {len(final_jobs)} scored jobs")

    # Save search history
    search = JobSearch(
        user_id=current_user.id,
        resume_id=resume.id,
        location=request.location or current_user.location,
        jobs_found=json.dumps(final_jobs[:50]),
        top_matches=json.dumps(final_jobs[:10])
    )
    db.add(search)
    db.commit()

    return {
        "status": "success",
        "resume_id": resume.id,
        "resume_skills": resume_skills,
        "search_keywords": search_keywords,
        "keyword_searches": search_results,
        "total_jobs_found": len(final_jobs),
        "jobs": final_jobs
    }


# ============================================================
# Helper Functions
# ============================================================
def normalize_time_filter(value: Optional[str]) -> str:
    """
    Validate and normalize the time_filter value.
    Returns 'any' if invalid or missing.
    """
    valid = {"24h", "7d", "30d", "any"}
    if value and value.lower() in valid:
        return value.lower()
    return "any"


def generate_search_keywords(skills: List[str]) -> List[str]:
    """Generate smart search keyword combinations from resume skills."""
    keywords = []
    clean_skills = [s.strip() for s in skills if s and s.strip()]

    if not clean_skills:
        return []

    for skill in clean_skills[:2]:
        keywords.append(f"{skill} Developer")
        keywords.append(f"{skill} Engineer")

    if len(clean_skills) >= 2:
        keywords.append(f"{clean_skills[0]} {clean_skills[1]}")
        keywords.append(f"{clean_skills[0]} {clean_skills[1]} Developer")

    if len(clean_skills) >= 3:
        keywords.append(f"{clean_skills[0]} {clean_skills[1]} {clean_skills[2]}")

    seen = set()
    unique = []
    for kw in keywords:
        kw = kw.strip()
        if kw and kw.lower() not in seen:
            seen.add(kw.lower())
            unique.append(kw)

    return unique


def score_job_against_skills(job: dict, resume_skills: List[str]) -> tuple:
    """Score how well a job matches the resume skills."""
    job_text_parts = [
        job.get("title", "") or "",
        job.get("description", "") or "",
        job.get("snippet", "") or "",
        job.get("requirements", "") or ""
    ]
    job_text = " ".join(job_text_parts).lower()

    resume_skills_clean = [s.lower().strip() for s in resume_skills if s and s.strip()]

    matched = []
    missing = []

    for skill in resume_skills_clean:
        if skill in job_text:
            matched.append(skill)
        else:
            missing.append(skill)

    if not resume_skills_clean:
        return 0, [], []

    score = int((len(matched) / len(resume_skills_clean)) * 100)

    job_title_lower = (job.get("title", "") or "").lower()
    for skill in resume_skills_clean:
        if skill in job_title_lower:
            score += 10
            break

    score = min(score, 100)

    return score, matched, missing