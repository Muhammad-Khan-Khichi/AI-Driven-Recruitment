"""
Smart filtering for job search results.
Filters by remote, salary, date posted, experience level, etc.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re


def filter_jobs(
    jobs: List[Dict],
    remote_only: Optional[bool] = None,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None,
    days_ago: Optional[int] = None,
    experience_level: Optional[str] = None,
    company_blacklist: Optional[List[str]] = None,
    keywords_required: Optional[List[str]] = None,
    keywords_excluded: Optional[List[str]] = None) -> List[Dict]:
    """
    Apply smart filters to job list.
    
    Args:
        jobs: List of job dicts
        remote_only: Only remote jobs
        min_salary: Minimum salary
        max_salary: Maximum salary
        days_ago: Posted within last N days
        experience_level: entry, mid, senior, lead
        company_blacklist: Skip these companies
        keywords_required: Must contain these in title/description
        keywords_excluded: Must NOT contain these
    """
    filtered = []
    
    # Normalize blacklist to lowercase
    blacklist = set()
    if company_blacklist:
        blacklist = {c.lower().strip() for c in company_blacklist}
    
    # Normalize keywords
    required_kw = [k.lower().strip() for k in (keywords_required or [])]
    excluded_kw = [k.lower().strip() for k in (keywords_excluded or [])]
    
    for job in jobs:
        #Remote filter
        if remote_only is not None:
            is_remote = _is_remote_job(job)
            if remote_only != is_remote:
                continue
        
        #Salary filter
        if min_salary is not None or max_salary is not None:
            job_min, job_max = _extract_salary(job)
            if min_salary is not None and job_max and job_max < min_salary:
                continue
            if max_salary is not None and job_min and job_min > max_salary:
                continue
        
        #Date filter
        if days_ago is not None:
            posted_date = _extract_posted_date(job)
            if posted_date:
                cutoff = datetime.now() - timedelta(days=days_ago)
                if posted_date < cutoff:
                    continue
        
        #Experience level
        if experience_level:
            job_level = _detect_experience_level(job)
            if job_level and job_level != experience_level.lower():
                continue
        
        #Company blacklist
        company = job.get("company", "").lower().strip()
        if company in blacklist:
            continue
        
        #Required keywords
        if required_kw:
            text = _job_to_searchable_text(job).lower()
            if not all(kw in text for kw in required_kw):
                continue
        
        #Excluded keywords
        if excluded_kw:
            text = _job_to_searchable_text(job).lower()
            if any(kw in text for kw in excluded_kw):
                continue
        
        # Job passed all filters
        filtered.append(job)
    
    return filtered


def _is_remote_job(job: Dict) -> bool:
    """Check if job is remote."""
    # Check explicit flag
    if job.get("remote") is True:
        return True
    
    # Check text fields
    text = _job_to_searchable_text(job).lower()
    remote_keywords = ["remote", "work from home", "wfh", "anywhere"]
    return any(kw in text for kw in remote_keywords)


def _extract_salary(job: Dict) -> tuple:
    """Extract (min, max) salary from job. Returns (None, None) if not found."""
    # Check explicit fields
    if job.get("salary_min") or job.get("salary_max"):
        return (job.get("salary_min"), job.get("salary_max"))
    
    # Parse from salary string
    salary_str = str(job.get("salary", ""))
    if not salary_str or salary_str.lower() in ["none", "null", ""]:
        return (None, None)
    
    # Find numbers (handle "$120k", "120000", "$120,000", etc.)
    numbers = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", salary_str)
    if not numbers:
        return (None, None)
    
    # Convert to floats
    nums = []
    for n in numbers:
        n_clean = n.replace(",", "")
        val = float(n_clean)
        # Handle "k" or "K" suffix
        if "k" in salary_str.lower():
            val *= 1000
        nums.append(val)
    
    if len(nums) == 1:
        return (nums[0], nums[0])
    elif len(nums) >= 2:
        return (min(nums), max(nums))
    
    return (None, None)


def _extract_posted_date(job: Dict) -> Optional[datetime]:
    """Extract posted date from job."""
    # Check explicit date field
    if job.get("posted_date"):
        try:
            if isinstance(job["posted_date"], datetime):
                return job["posted_date"]
            return datetime.fromisoformat(str(job["posted_date"]))
        except:
            pass
    
    # Parse from date string (e.g., "2 days ago", "2024-01-15")
    date_str = str(job.get("date", "") or job.get("posted", ""))
    if not date_str:
        return None
    
    # Try ISO format first
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except:
        pass
    
    # Try "X days ago" format
    days_match = re.search(r"(\d+)\s*day", date_str.lower())
    if days_match:
        days = int(days_match.group(1))
        return datetime.now() - timedelta(days=days)
    
    # Try "X hours ago"
    hours_match = re.search(r"(\d+)\s*hour", date_str.lower())
    if hours_match:
        hours = int(hours_match.group(1))
        return datetime.now() - timedelta(hours=hours)
    
    return None


def _detect_experience_level(job: Dict) -> Optional[str]:
    """Detect experience level from job title/description."""
    title = str(job.get("title", "")).lower()
    desc = str(job.get("description", "")).lower()
    text = f"{title} {desc}"
    
    # Check from most specific to least
    if any(kw in title for kw in ["lead", "principal", "staff", "head of"]):
        return "lead"
    if any(kw in title for kw in ["senior", "sr.", "sr ", "expert"]):
        return "senior"
    if any(kw in title for kw in ["junior", "jr.", "jr ", "entry", "intern", "graduate"]):
        return "entry"
    if any(kw in title for kw in ["mid", "intermediate"]):
        return "mid"
    
    # Check description for years of experience
    years_match = re.search(r"(\d+)\+?\s*years", desc)
    if years_match:
        years = int(years_match.group(1))
        if years >= 7:
            return "lead"
        elif years >= 4:
            return "senior"
        elif years >= 2:
            return "mid"
        else:
            return "entry"
    
    return None


def _job_to_searchable_text(job: Dict) -> str:
    """Convert job to searchable text."""
    parts = [
        str(job.get("title", "")),
        str(job.get("company", "")),
        str(job.get("location", "")),
        str(job.get("description", "")),
        str(job.get("salary", "")),
    ]
    if job.get("skills"):
        parts.append(", ".join(str(s) for s in job["skills"]))
    return " ".join(parts)
