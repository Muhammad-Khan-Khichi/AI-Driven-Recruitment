import requests
import json
import time
from langchain_core.tools import tool

from config import settings
from utils import get_logger

logger = get_logger(__name__)

# LinkedIn's time filter codes (24h, 7d, 30d, any)
LINKEDIN_TIME_FILTERS = {
    "24h":  "r86400",
    "7d":   "r604800",
    "30d":  "r2592000",
    "any":  "",
}


def normalize_time_filter(value):
    """Validate time_filter, default to 'any'."""
    valid = {"24h", "7d", "30d", "any"}
    if value and str(value).lower() in valid:
        return str(value).lower()
    return "any"


def search_adzuna(query: str, location: str = None, time_filter: str = "any") -> list:
    """
    ⚠️ DISABLED - Adzuna only works for UK/US/IN/AU.
    Returns 0 jobs for Pakistan and most countries.
    """
    logger.info(f"⏭️  Adzuna skipped (disabled - not global, filter: {time_filter})")
    return []


def search_jooble(query: str, location: str = None, time_filter: str = "any") -> list:
    """
    ⚠️ DISABLED - Jooble has limited country support.
    Returns 0 jobs for Pakistan and most countries.
    """
    logger.info(f"⏭️  Jooble skipped (disabled - not global, filter: {time_filter})")
    return []


def search_indeed_rss(query: str, location: str = "Lahore, Pakistan", time_filter: str = "any") -> list:
    """
    ⚠️ DISABLED - Indeed RSS often blocked.
    LinkedIn is more reliable for global search.
    """
    logger.info(f"⏭️  Indeed RSS skipped (disabled - LinkedIn only, filter: {time_filter})")
    return []


def search_all_sources(query: str, location: str = None, time_filter: str = "any") -> list:
    """
    Search jobs - LINKEDIN ONLY! 🎯
    
    Why LinkedIn only?
    ✅ Works for ALL countries (Pakistan, US, UK, India, etc.)
    ✅ Returns real, fresh job listings
    ✅ Fastest (~20s per search)
    ✅ No API key needed
    
    Disabled sources:
    ❌ Adzuna - only UK/US/IN/AU (returned 0 for Pakistan)
    ❌ Jooble - limited country support (returned 0 for Pakistan)
    ❌ Indeed RSS - often blocked, inconsistent
    """
    location = location or settings.DEFAULT_LOCATION
    time_filter = normalize_time_filter(time_filter)

    # Import here to avoid circular imports
    from .linkedin_scraper import search_linkedin_jobs

    all_jobs = []
    
    # LinkedIn only - works globally!
    try:
        linkedin_jobs = search_linkedin_jobs(query, location, time_filter=time_filter)
        all_jobs.extend(linkedin_jobs)
        logger.info(f"✅ LinkedIn returned {len(linkedin_jobs)} jobs for '{query}' in '{location}' (filter: {time_filter})")
    except Exception as e:
        logger.warning(f"❌ LinkedIn search failed for '{query}' in '{location}': {e}")

    return all_jobs


@tool
def search_jobs(query: str, location: str = "Lahore", time_filter: str = "any") -> str:
    """Search jobs from LinkedIn (global coverage)."""
    jobs = search_all_sources(query, location, time_filter=time_filter)
    return json.dumps(jobs, indent=2)