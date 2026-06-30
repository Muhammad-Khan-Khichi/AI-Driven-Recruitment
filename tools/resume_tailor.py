import os
import time
from langchain_mistralai import ChatMistralAI

from config import settings  # Add this line
from utils import get_logger  # Add this if you want logging

logger = get_logger(__name__)

_llm = ChatMistralAI(
    model=settings.MISTRAL_MODEL,
    temperature=0.3,
    api_key=settings.MISTRAL_API_KEY
)


def _invoke_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Call LLM with retry logic for rate limits."""
    for attempt in range(max_retries):
        try:
            response = _llm.invoke(prompt)
            return response.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = 2 ** attempt
                logger.warning(f"Rate limit hit, waiting {wait}s")
                time.sleep(wait)
            else:
                raise
    return '{"missing_keywords": [], "suggested_additions": [], "sections_to_emphasize": []}'


def tailor_resume(resume_text, job):
    """Suggest resume modifications for a specific job."""
    prompt = f"""Given this resume and job, suggest specific edits to improve match.

Resume:
{resume_text[:2000]}

Job: {job.get('title')} at {job.get('company')}
Description: {job.get('snippet')}

Return JSON with:
- "missing_keywords": [list of keywords from job missing in resume]
- "suggested_additions": [specific bullet points to add]
- "sections_to_emphasize": [which parts to highlight]
"""

    return _invoke_with_retry(prompt)