import requests
from config import settings
from utils import get_logger

logger = get_logger(__name__)


def search_indeed(query: str, location: str = "Lahore, Pakistan") -> list:
    """
    Search Indeed jobs via their public RSS feed.
    RSS feeds are publicly accessible and not blocked like HTML scraping.
    """
    try:
        # Indeed RSS feed - works without API key
        url = "https://indeed.com/rss"
        params = {
            "q": query,
            "l": location,
            "limit": 15
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse XML response
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)

        jobs = []
        for item in root.findall(".//item")[:15]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            source = item.findtext("source", "Indeed")

            jobs.append({
                "title": title,
                "company": source,
                "location": location,
                "url": link,
                "snippet": description[:400] if description else "",
                "source": "Indeed RSS",
                "posted": pub_date
            })

        logger.info(f"Indeed RSS returned {len(jobs)} jobs for '{query}'")
        return jobs
    except Exception as e:
        logger.warning(f"Indeed RSS error: {e}")
        return []


def search_rozee_pk(query: str, location: str = "Lahore") -> list:
    """Rozee.pk - Pakistan's largest job board."""
    try:
        url = "https://www.rozee.pk/api/job/search"
        params = {
            "q": query,
            "city": location,
            "limit": 15
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            jobs = []
            for job in data.get("jobs", [])[:15]:
                jobs.append({
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("city", location),
                    "url": f"https://www.rozee.pk/job/{job.get('id')}",
                    "snippet": job.get("description", "")[:400],
                    "source": "Rozee.pk"
                })
            logger.info(f"Rozee.pk returned {len(jobs)} jobs")
            return jobs
    except Exception as e:
        logger.warning(f"Rozee.pk error: {e}")
    return []