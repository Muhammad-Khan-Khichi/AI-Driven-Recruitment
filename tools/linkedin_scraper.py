import requests
from bs4 import BeautifulSoup
from config import settings
from utils import get_logger

logger = get_logger(__name__)


def search_linkedin_jobs(query: str, location: str = "Lahore") -> list:
    """
    Search LinkedIn jobs (public listings, no login required).
    Note: LinkedIn may block scraping - use as fallback only.
    """
    try:
        # LinkedIn's public guest job search endpoint
        url = "https://www.linkedin.com/jobs/search"
        params = {
            "keywords": query,
            "location": f"{location}, Pakistan",
            "f_TPR": "r86400",  # Last 24 hours
            "position": 1,
            "pageNum": 0
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = requests.get(url, params=params, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        # LinkedIn job cards have this class
        for card in soup.find_all("div", class_="base-card")[:15]:
            title_tag = card.find("h3", class_="base-search-card__title")
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            location_tag = card.find("span", class_="job-search-card__location")
            link_tag = card.find("a", class_="base-card__full-link")

            if title_tag and link_tag:
                jobs.append({
                    "title": title_tag.get_text(strip=True),
                    "company": company_tag.get_text(strip=True) if company_tag else "Unknown",
                    "location": location_tag.get_text(strip=True) if location_tag else location,
                    "url": link_tag.get("href", "").split("?")[0],
                    "snippet": "",
                    "source": "LinkedIn"
                })

        logger.info(f"LinkedIn returned {len(jobs)} jobs for '{query}'")
        return jobs
    except Exception as e:
        logger.warning(f"LinkedIn scraping failed: {e}")
        return []