import json
from typing import Any, List, Dict


def safe_json_loads(text: str) -> Any:
    """Parse JSON from LLM output, handling markdown code blocks."""
    text = text.strip()

    # Remove markdown code fences
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def deduplicate_jobs(jobs: List[Dict]) -> List[Dict]:
    """Remove duplicate jobs by URL."""
    seen = set()
    unique = []
    for job in jobs:
        url = job.get("url") or job.get("link")
        if url and url not in seen:
            seen.add(url)
            unique.append(job)
    return unique


def save_results(data: Any, filepath: str) -> None:
    """Save results to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)