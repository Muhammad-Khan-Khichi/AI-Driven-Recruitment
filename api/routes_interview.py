
"""Interview prep API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from agent.interview_prep import InterviewPrep


router = APIRouter(prefix="/api/interview", tags=["interview"])


class GenerateQuestionsRequest(BaseModel):
    """Request to generate interview questions."""
    job_title: str
    job_description: str
    num_questions: int = 10
    question_types: Optional[List[str]] = None


class EvaluateAnswerRequest(BaseModel):
    """Request to evaluate an interview answer."""
    question: str
    answer: str
    question_type: str = "behavioral"


class StudyPlanRequest(BaseModel):
    """Request for study plan."""
    job_title: str
    job_description: str
    days_until_interview: int = 7


@router.post("/questions")
async def generate_questions(req: GenerateQuestionsRequest):
    """
    Generate interview questions for a job.
    Returns list with type, difficulty, tips, and sample answers.
    """
    try:
        prep = InterviewPrep()
        questions = prep.generate_questions(
            job_title=req.job_title,
            job_description=req.job_description,
            num_questions=req.num_questions,
            question_types=req.question_types
        )
        return {
            "job_title": req.job_title,
            "total": len(questions),
            "questions": questions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate")
async def evaluate_answer(req: EvaluateAnswerRequest):
    """
    Evaluate a candidate's answer.
    Returns score, feedback, strengths, and improvements.
    """
    try:
        prep = InterviewPrep()
        result = prep.evaluate_answer(
            question=req.question,
            answer=req.answer,
            question_type=req.question_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/study-plan")
async def study_plan(req: StudyPlanRequest):
    """
    Generate a study plan for interview prep.
    """
    try:
        prep = InterviewPrep()
        result = prep.generate_study_plan(
            job_title=req.job_title,
            job_description=req.job_description,
            days_until_interview=req.days_until_interview
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))