"""LinkedIn optimization API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from agent.linkedin_optimizer import LinkedInOptimizer


router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


class OptimizeProfileRequest(BaseModel):
    """Request to optimize LinkedIn profile."""
    current_headline: Optional[str] = None
    current_about: Optional[str] = None
    current_skills: Optional[List[str]] = None
    target_role: Optional[str] = None
    years_experience: Optional[int] = None
    industry: Optional[str] = None


class OptimizeHeadlineRequest(BaseModel):
    """Request to optimize just the headline."""
    current_headline: str
    target_role: str


@router.post("/optimize-profile")
async def optimize_profile(req: OptimizeProfileRequest):
    """
    Optimize full LinkedIn profile.
    Returns improved headline, about, skills, and tips.
    """
    try:
        optimizer = LinkedInOptimizer()
        result = optimizer.optimize_profile(
            current_headline=req.current_headline,
            current_about=req.current_about,
            current_skills=req.current_skills,
            target_role=req.target_role,
            years_experience=req.years_experience,
            industry=req.industry
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize-headline")
async def optimize_headline(req: OptimizeHeadlineRequest):
    """
    Quick headline-only optimization.
    Returns improved headline + alternatives.
    """
    try:
        optimizer = LinkedInOptimizer()
        result = optimizer.optimize_headline_only(
            current_headline=req.current_headline,
            target_role=req.target_role
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))