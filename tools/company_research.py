# tools/company_research.py
import requests

def research_company(company_name):
    """Get company info from public sources."""
    # Wikipedia API
    wiki = requests.get(
        "https://en.wikipedia.org/api/rest_v1/page/summary/" + company_name.replace(" ", "_")
    ).json()

    # Glassdoor / Google search fallback
    return {
        "name": company_name,
        "description": wiki.get("extract"),
        "url": wiki.get("content_urls", {}).get("desktop", {}).get("page")
    }