import time
from langchain_mistralai import ChatMistralAI

from agent.prompts import JOB_ALERT_FILTER_PROMPT
from config import settings
from utils import get_logger, safe_json_loads

logger = get_logger(__name__)

_llm = ChatMistralAI(
    model="mistral-tiny",
    temperature=0,
    api_key=settings.MISTRAL_API_KEY
)


def _invoke_with_retry(prompt: str, max_retries: int = 5) -> str:
    """Call LLM with retry logic for rate limits."""
    for attempt in range(max_retries):
        try:
            response = _llm.invoke(prompt)
            return response.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = min(2 ** attempt, 30)  # 1, 2, 4, 8, 16, capped at 30s
                logger.warning(f"Rate limit hit, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
    # Fallback: return a default score instead of failing
    return '{"match_score": 50, "reason": "Rate limit reached - default neutral score"}'


def filter_jobs_with_ai(jobs: list, profile: dict, min_score: int = 60) -> list:
    """Use AI to filter and score jobs based on profile match."""
    filtered = []

    for i, job in enumerate(jobs):
        try:
            prompt = JOB_ALERT_FILTER_PROMPT.format(
                skills=", ".join(profile.get("skills", [])),
                job_titles=", ".join(profile.get("job_titles", [])),
                job_title=job.get("title", ""),
                company=job.get("company", ""),
                description=job.get("snippet", "")
            )

            content = _invoke_with_retry(prompt)
            result = safe_json_loads(content)
            score = result.get("match_score", 0)

            job["score"] = score
            job["match_reason"] = result.get("reason", "")

            if score >= min_score:
                filtered.append(job)

            # Longer delay to avoid hitting rate limits
            time.sleep(2)

        except Exception as e:
            logger.warning(f"Filter error for job {job.get('title')}: {e}")
            job["score"] = 50
            filtered.append(job)

    filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
    return filtered