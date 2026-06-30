import requests
import json
import time
from langchain_core.tools import tool

from config import settings
from utils import get_logger

logger = get_logger(__name__)


def search_adzuna(query: str, location: str = None) -> list:
    """Search Adzuna API with country fallback."""
    location = location or settings.DEFAULT_LOCATION

    if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
        return []

    for country in ["gb", "in", "us", "au"]:
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "results_per_page": settings.MAX_JOBS_PER_QUERY,
            "what": query,
            "where": location,
            "content-type": "application/json"
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            data = response.json()

            jobs = []
            for job in data.get("results", []):
                jobs.append({
                    "title": job.get("title"),
                    "company": (job.get("company") or {}).get("display_name"),
                    "location": (job.get("location") or {}).get("display_name"),
                    "url": job.get("redirect_url"),
                    "snippet": (job.get("description") or "")[:400],
                    "source": f"Adzuna ({country})"
                })
            logger.info(f"Adzuna ({country}) returned {len(jobs)} jobs for '{query}'")
            return jobs
        except Exception:
            continue

    return []


def search_jooble(query: str, location: str = None) -> list:
    """Search Jooble API."""
    location = location or settings.DEFAULT_LOCATION

    if not settings.JOOBLE_API_KEY:
        logger.warning("Jooble API key not configured")
        return []

    url = f"https://jooble.org/api/{settings.JOOBLE_API_KEY}"
    payload = {
        "keywords": query,
        "location": location,
        "radius": "25",
        "resultNumber": settings.MAX_JOBS_PER_QUERY
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        jobs = []
        for job in data.get("jobs", []):
            job_title = (job.get("title") or "").lower()
            job_location = (job.get("location") or "").lower()
            job_snippet = (job.get("snippet") or "").lower()

            # Accept if any Pakistan/Lahore keyword appears, OR if no location filter applies
            pakistan_keywords = ["pakistan", "lahore", "karachi", "islamabad", "rawalpindi", "faisalabad"]
            is_pakistan = any(k in job_location or k in job_snippet for k in pakistan_keywords)

            # If location is empty/unknown, include it
            if not job_location or is_pakistan:
                jobs.append({
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "salary": job.get("salary"),
                    "url": job.get("link"),
                    "snippet": job.get("snippet", "")[:400],
                    "source": "Jooble"
                })

        logger.info(f"Jooble returned {len(jobs)} jobs for '{query}' in {location}")
        return jobs
    except Exception as e:
        logger.error(f"Jooble error: {e}")
        return []

def search_indeed_rss(query: str, location: str = "Lahore, Pakistan") -> list:
    """Search Indeed via RSS feed (public, no API key needed)."""
    try:
        import xml.etree.ElementTree as ET

        url = "https://indeed.com/rss"
        params = {"q": query, "l": location}
        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        jobs = []

        for item in root.findall(".//item")[:15]:
            jobs.append({
                "title": item.findtext("title", ""),
                "company": item.findtext("source", "Indeed"),
                "location": location,
                "url": item.findtext("link", ""),
                "snippet": (item.findtext("description", "") or "")[:400],
                "source": "Indeed"
            })

        logger.info(f"Indeed RSS returned {len(jobs)} jobs for '{query}'")
        return jobs
    except Exception as e:
        logger.warning(f"Indeed RSS error: {e}")
        return []


def search_all_sources(query: str, location: str = None) -> list:
    """Search all available job sources."""
    location = location or settings.DEFAULT_LOCATION

    # Import here to avoid circular imports
    from .linkedin_scraper import search_linkedin_jobs

    all_jobs = []
    all_jobs.extend(search_adzuna(query, location))
    all_jobs.extend(search_jooble(query, location))
    all_jobs.extend(search_linkedin_jobs(query, location))

    return all_jobs


@tool
def search_jobs(query: str, location: str = "Lahore") -> str:
    """Search jobs from multiple sources."""
    jobs = search_all_sources(query, location)
    return json.dumps(jobs, indent=2)


def search_indeed_rss(query: str, location: str = "Lahore, Pakistan") -> list:
    """Search Indeed via public RSS feed (no API key needed)."""
    try:
        import xml.etree.ElementTree as ET

        url = "https://indeed.com/rss"
        params = {"q": query, "l": location}
        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        jobs = []

        for item in root.findall(".//item")[:15]:
            jobs.append({
                "title": item.findtext("title", ""),
                "company": item.findtext("source", "Indeed"),
                "location": location,
                "url": item.findtext("link", ""),
                "snippet": (item.findtext("description", "") or "")[:400],
                "source": "Indeed"
            })

        logger.info(f"Indeed RSS returned {len(jobs)} jobs for '{query}'")
        return jobs
    except Exception as e:
        logger.warning(f"Indeed RSS error: {e}")
        return []