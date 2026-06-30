import json
from langchain_mistralai import ChatMistralAI

from agent.prompts import JOB_RANKING_PROMPT, COVER_LETTER_PROMPT
from config import settings
from utils import get_logger

logger = get_logger(__name__)

_llm = ChatMistralAI(
    model=settings.MISTRAL_MODEL,
    temperature=settings.TEMPERATURE,
    api_key=settings.MISTRAL_API_KEY
)


def rank_jobs(jobs: list, profile: dict) -> str:
    """Rank jobs using LLM based on candidate profile."""
    if not jobs:
        return "No jobs to rank."

    jobs_text = json.dumps(jobs[:20], indent=2)
    prompt = JOB_RANKING_PROMPT.format(
        skills=", ".join(profile.get("skills", [])),
        job_titles=", ".join(profile.get("job_titles", [])),
        level=profile.get("level", "mid"),
        num_jobs=len(jobs),
        jobs_text=jobs_text
    )

    response = _llm.invoke(prompt)
    return response.content


def generate_cover_letter(skills: list, job: dict) -> str:
    """Generate a tailored cover letter for a specific job."""
    prompt = COVER_LETTER_PROMPT.format(
        skills=", ".join(skills),
        job_title=job.get("title", "Unknown"),
        company=job.get("company", "Unknown"),
        description=job.get("snippet", "")
    )
    response = _llm.invoke(prompt)
    return response.content