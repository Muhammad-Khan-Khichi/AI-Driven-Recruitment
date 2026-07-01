from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from database.db import get_db, User, Resume, JobSearch, Application
from api.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---- Pydantic schemas ----
class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None 
    is_admin: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None   

    class Config:
        from_attributes = True


class Stats(BaseModel):
    total_users: int
    total_admins: int
    total_resumes: int
    total_searches: int
    total_applications: int
    users_today: int


# ---- Dependency: require admin ----
def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# ---- Routes ----
@router.get("/stats", response_model=Stats)
def get_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    today = datetime.utcnow() - timedelta(days=1)

    return {
        "total_users": db.query(User).count(),
        "total_admins": db.query(User).filter(User.is_admin == True).count(),
        "total_resumes": db.query(Resume).count(),
        "total_searches": db.query(JobSearch).count(),
        "total_applications": db.query(Application).count(),
        "users_today": db.query(User).filter(User.created_at >= today).count(),
    }


@router.get("/users", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 100
):
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/{user_id}/make-admin")
def make_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = True
    db.commit()
    return {"detail": f"User '{user.username}' is now an admin"}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user.is_active = False
    db.commit()
    return {"detail": f"User '{user.username}' deactivated"}


@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    return {"detail": f"User '{user.username}' activated"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Cascade delete related rows
    db.query(Resume).filter(Resume.user_id == user_id).delete()
    db.query(JobSearch).filter(JobSearch.user_id == user_id).delete()
    db.query(Application).filter(Application.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"detail": f"User '{user.username}' deleted"}


@router.get("/resumes")
def list_all_resumes(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 100
):
    resumes = db.query(Resume).order_by(Resume.uploaded_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "username": r.user.username if r.user else None,
            "filename": r.filename,
            "extracted_skills": r.extracted_skills,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
        }
        for r in resumes
    ]


@router.get("/searches")
def list_all_searches(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 100
):
    searches = db.query(JobSearch).order_by(JobSearch.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "username": s.user.username if s.user else None,
            "location": s.location,
            "jobs_found": s.jobs_found,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in searches
    ]


@router.get("/applications")
def list_all_applications(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 100
):
    apps = db.query(Application).order_by(Application.applied_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "username": a.user.username if a.user else None,
            "job_title": a.job_title,
            "company": a.company,
            "status": a.status,
            "applied_at": a.applied_at.isoformat() if a.applied_at else None,
        }
        for a in apps
    ]
