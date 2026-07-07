import requests
from bs4 import BeautifulSoup
from config import settings
from utils import get_logger

logger = get_logger(__name__)

# LinkedIn's time filter codes
LINKEDIN_TIME_FILTERS = {
    "24h":   "r86400",     # Last 24 hours
    "7d":    "r604800",    # Last 7 days
    "30d":   "r2592000",   # Last 30 days
    "any":   "",           # No filter
}


def search_linkedin_jobs(query: str, location: str = "Lahore", time_filter: str = "any") -> list:
    """
    Search LinkedIn jobs (public listings, no login required).
    
    Args:
        query: Search keywords
        location: Location string (e.g. "London", "Remote")
        time_filter: '24h', '7d', '30d', or 'any'
    """
    try:
        url = "https://www.linkedin.com/jobs/search"
        
        # Build params WITHOUT hardcoded "Pakistan"
        params = {
            "keywords": query,
            "location": location,  # ✅ FIX: no more "f'{location}, Pakistan'"
            "position": 1,
            "pageNum": 0
        }
        
        # ✅ NEW: Apply time filter only if not "any"
        tpr_code = LINKEDIN_TIME_FILTERS.get(time_filter, "")
        if tpr_code:
            params["f_TPR"] = tpr_code
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = requests.get(url, params=params, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
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
                    "source": "LinkedIn",
                    "posted_within": time_filter  # Pass through for UI
                })

        logger.info(f"LinkedIn returned {len(jobs)} jobs for '{query}' in '{location}' (filter: {time_filter})")
        return jobs
    except Exception as e:
        logger.warning(f"LinkedIn scraping failed: {e}")
        return []