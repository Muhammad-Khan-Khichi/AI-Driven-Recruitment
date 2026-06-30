
"""Resume optimization API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from agent.resume_optimizer import ResumeOptimizer, quick_ats_score


router = APIRouter(prefix="/api/resume", tags=["resume"])


class OptimizeRequest(BaseModel):
    """Request to optimize a resume."""
    resume_text: str
    job_description: str
    job_title: Optional[str] = None


class QuickScoreRequest(BaseModel):
    """Request for quick ATS score."""
    resume_text: str
    job_description: str


@router.post("/optimize")
async def optimize_resume(req: OptimizeRequest):
    """
    Optimize resume for a specific job.
    Returns ATS score, missing keywords, weak bullets, and suggested improvements.
    """
    try:
        optimizer = ResumeOptimizer()
        result = optimizer.optimize(
            resume_text=req.resume_text,
            job_description=req.job_description,
            job_title=req.job_title
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-score")
async def quick_score(req: QuickScoreRequest):
    """
    Get quick ATS score (0-100) without AI.
    Useful for fast keyword match check.
    """
    try:
        score = quick_ats_score(req.resume_text, req.job_description)
        return {
            "ats_score": score,
            "interpretation": _interpret_score(score)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _interpret_score(score: int) -> str:
    """Interpret ATS score."""
    if score >= 80:
        return "Excellent match - strong candidate"
    elif score >= 60:
        return "Good match - some improvements needed"
    elif score >= 40:
        return "Moderate match - significant gaps to address"
    elif score >= 20:
        return "Weak match - major improvements needed"
    else:
        return "Poor match - consider if this role fits your background"