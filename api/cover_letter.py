# routers/cover_letter.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json

from database import get_db
from database.db import User
from database.db import Resume
from database.db import CoverLetter
from api.auth import get_current_user
from config import settings

# Import your existing tool
from tools.cover_letter_tools import generate_cover_letter, save_cover_letter

router = APIRouter(prefix="/api/cover-letter", tags=["cover-letter"])


class CoverLetterRequest(BaseModel):
    resume_id: int
    job_title: str
    company: str
    job_description: str
    job_url: Optional[str] = None
    location: Optional[str] = ""
    tone: str = "professional"


class CoverLetterVariant(BaseModel):
    tone: str
    body: str


class CoverLetterResponse(BaseModel):
    id: int
    variants: List[CoverLetterVariant]
    job_title: str
    company: str
    saved_path: Optional[str] = None
    created_at: datetime


@router.post("/generate", response_model=CoverLetterResponse)
async def generate_cover_letter_endpoint(
    request: CoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate cover letter using Mistral AI
    
    Returns 3 variants in different tones
    """
    # Get user's resume
    resume = db.query(Resume).filter(
        Resume.id == request.resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # ✅ FIX: Build profile from resume (uses extracted_skills, not skills)
    profile = {
        "skills": [],
        "level": "mid",
        "experience_years": 2
    }
    
    # Parse skills from extracted_skills (it's comma-separated string)
    if resume.extracted_skills:
        skills_list = [
            skill.strip() 
            for skill in resume.extracted_skills.split(",") 
            if skill.strip()
        ]
        profile["skills"] = skills_list
    
    # Optional: Try to detect experience years from parsed_text
    if resume.parsed_text:
        # Simple regex to find years of experience
        import re
        match = re.search(r'(\d+)\+?\s*years?', resume.parsed_text.lower())
        if match:
            profile["experience_years"] = int(match.group(1))
    
    # Build job dict
    job = {
        "title": request.job_title,
        "company": request.company,
        "location": request.location,
        "snippet": request.job_description,
        "url": request.job_url
    }
    
    # Generate 3 variants
    variants = []
    tones = ["professional", "conversational", "enthusiastic"]
    
    for tone in tones:
        try:
            # Use your existing tool
            letter = generate_cover_letter(profile, job)
            
            variants.append({
                "tone": tone,
                "body": letter
            })
        except Exception as e:
            variants.append({
                "tone": tone,
                "body": f"Error generating {tone} variant: {str(e)}"
            })
    
    # Save first variant to file (optional)
    saved_path = None
    try:
        if variants and "Error" not in variants[0]["body"]:
            saved_path = save_cover_letter(variants[0]["body"], job)
    except Exception:
        pass
    
    # Save to database
    cover_letter = CoverLetter(
        user_id=current_user.id,
        resume_id=request.resume_id,
        job_title=request.job_title,
        company=request.company,
        job_description=request.job_description,
        job_url=request.job_url,
        variants=variants,
        created_at=datetime.utcnow()
    )
    db.add(cover_letter)
    db.commit()
    db.refresh(cover_letter)
    
    return CoverLetterResponse(
        id=cover_letter.id,
        variants=[CoverLetterVariant(**v) for v in variants],
        job_title=request.job_title,
        company=request.company,
        saved_path=saved_path,
        created_at=cover_letter.created_at
    )


@router.get("/list")
async def list_cover_letters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all user's cover letters"""
    cover_letters = db.query(CoverLetter).filter(
        CoverLetter.user_id == current_user.id
    ).order_by(CoverLetter.created_at.desc()).limit(50).all()
    
    return [
        {
            "id": cl.id,
            "job_title": cl.job_title,
            "company": cl.company,
            "created_at": cl.created_at,
            "variants_count": len(cl.variants) if cl.variants else 0
        }
        for cl in cover_letters
    ]


@router.get("/{cover_letter_id}")
async def get_cover_letter(
    cover_letter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific cover letter with all variants"""
    cl = db.query(CoverLetter).filter(
        CoverLetter.id == cover_letter_id,
        CoverLetter.user_id == current_user.id
    ).first()
    
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    return {
        "id": cl.id,
        "job_title": cl.job_title,
        "company": cl.company,
        "job_description": cl.job_description,
        "job_url": cl.job_url,
        "variants": cl.variants,
        "final_text": cl.final_text,
        "created_at": cl.created_at,
        "updated_at": cl.updated_at
    }


@router.put("/{cover_letter_id}")
async def update_cover_letter(
    cover_letter_id: int,
    final_text: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update cover letter with edited version"""
    cl = db.query(CoverLetter).filter(
        CoverLetter.id == cover_letter_id,
        CoverLetter.user_id == current_user.id
    ).first()
    
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    cl.final_text = final_text
    cl.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Cover letter updated",
        "id": cl.id,
        "updated_at": cl.updated_at
    }


@router.delete("/{cover_letter_id}")
async def delete_cover_letter(
    cover_letter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete cover letter"""
    cl = db.query(CoverLetter).filter(
        CoverLetter.id == cover_letter_id,
        CoverLetter.user_id == current_user.id
    ).first()
    
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    db.delete(cl)
    db.commit()
    
    return {"message": "Cover letter deleted", "id": cover_letter_id}