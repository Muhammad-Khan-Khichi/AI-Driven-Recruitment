import os
import time
from datetime import datetime
from langchain_mistralai import ChatMistralAI

from agent.prompts import COVER_LETTER_PROMPT
from config import settings
from utils import get_logger

logger = get_logger(__name__)

_llm = ChatMistralAI(
    model="mistral-small-latest",
    temperature=0.7,
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
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Rate limit hit, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
    return "Cover letter generation failed due to rate limits. Please try again later."


def generate_cover_letter(profile: dict, job: dict) -> str:
    """Generate a tailored cover letter for one job."""
    prompt = COVER_LETTER_PROMPT.format(
        skills=", ".join(profile.get("skills", [])),
        level=profile.get("level", "mid"),
        years=profile.get("experience_years", 2),
        job_title=job.get("title", "Unknown"),
        company=job.get("company", "Unknown"),
        location=job.get("location", ""),
        description=job.get("snippet", "")
    )
    return _invoke_with_retry(prompt)


def save_cover_letter(letter: str, job: dict) -> str:
    """Save cover letter to file and return file path."""
    os.makedirs(settings.COVER_LETTERS_DIR, exist_ok=True)

    company = (job.get("company") or "company").replace(" ", "_").replace("/", "-")
    title = (job.get("title") or "role").replace(" ", "_").replace("/", "-")[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company}_{title}_{timestamp}.txt"
    filepath = os.path.join(settings.COVER_LETTERS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Cover Letter for: {job.get('title')} at {job.get('company')}\n")
        f.write(f"Apply at: {job.get('url')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        f.write(letter)

    logger.info(f"Cover letter saved: {filepath}")
    return filepath


def generate_cover_letters_for_top_matches(profile: dict, ranked_jobs: list, top_n: int = 3) -> list:
    """Generate cover letters for top N job matches."""
    saved_letters = []

    for i, job in enumerate(ranked_jobs[:top_n], 1):
        logger.info(f"Generating cover letter {i}/{top_n} for: {job.get('title')}")
        letter = generate_cover_letter(profile, job)
        filepath = save_cover_letter(letter, job)
        saved_letters.append({
            "job_title": job.get("title"),
            "company": job.get("company"),
            "file_path": filepath,
            "letter_preview": letter[:200] + "..."
        })
        # Small delay between cover letters
        time.sleep(1)

    return saved_letters