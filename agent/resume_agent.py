"""Job search agent with both CLI and API interfaces."""

import os
from langchain_mistralai import ChatMistralAI

from config import settings
from utils import get_logger, deduplicate_jobs, save_results
from tools import (
    load_resume_text,
    extract_skills_from_resume,
    search_all_sources,
    rank_jobs,
    generate_cover_letters_for_top_matches,
    filter_jobs_with_ai
)
from agent.vector_store import JobVectorStore, ResumeVectorStore
from agent.semantic_search import SemanticJobSearch

logger = get_logger(__name__)


def safe_len(value, default=0):
    """Safely get length of a value (handles int, None, str, list, etc.)."""
    if value is None:
        return default
    try:
        return len(value)
    except TypeError:
        if isinstance(value, (int, float)):
            return int(abs(value))
        return default


class JobFinderAgent:
    def __init__(self, generate_letters: bool = True):
        self.llm = ChatMistralAI(
            model=settings.MISTRAL_MODEL,
            temperature=settings.TEMPERATURE,
            api_key=settings.MISTRAL_API_KEY
        )
        self.location = settings.DEFAULT_LOCATION
        self.generate_letters = generate_letters
        self.last_vector_stats = None

    def run(
        self,
        resume_path: str = None,           # ⚡ Optional now
        resume_text: str = "",             # ⚡ NEW: accept text directly
        candidate_name: str = "Candidate",
        user_id: int = None,
        custom_keywords: list = None
    ) -> dict:
        """Main agent workflow with semantic + AI hybrid ranking."""
        logger.info(f"Starting job search for: {resume_path or 'text input'}")

        # ─── Step 1: Load resume (⚡ Use text from DB if provided!) ───
        logger.info("[1/5] Loading resume")
        
        if resume_text and len(resume_text) > 100:
            # ⚡ FAST! Use text directly from DB
            logger.info(f"  ⚡ Using resume text from DB ({len(resume_text)} chars)")
        elif resume_path and os.path.exists(resume_path):
            # Fallback: load from file
            logger.info(f"  📄 Loading resume from file: {resume_path}")
            resume_text = load_resume_text(resume_path)
        else:
            logger.warning(f"  ⚠️  No resume content available!")
            resume_text = ""

        # ─── Step 2: Extract profile ──────────────────────────
        logger.info("[2/5] Extracting profile")
        profile = extract_skills_from_resume(resume_text)
        profile["name"] = candidate_name
        profile["resume_path"] = resume_path or "(from DB)"

        logger.info(f"  Skills: {safe_len(profile.get('skills', []))}")
        logger.info(f"  Roles:  {profile.get('job_titles', [])[:3]}")

        # ─── Step 3: Search jobs from external APIs ─────────
        logger.info("[3/5] Searching job boards")
        all_jobs = []

        # ⚡ Use custom_keywords if provided, else fall back to resume job_titles
        if custom_keywords and len(custom_keywords) > 0:
            search_terms = custom_keywords[:2]  # ⚡ Only 2 keywords (was 5)
            logger.info(f"  Using {safe_len(search_terms)} custom keywords: {search_terms}")
        else:
            search_terms = profile.get("job_titles", [])[:2]  # ⚡ Only 2 (was 3)
            logger.info(f"  Using {safe_len(search_terms)} resume-extracted roles")

        for term in search_terms:
            jobs = search_all_sources(term, self.location)
            all_jobs.extend(jobs)

        unique_jobs = deduplicate_jobs(all_jobs)
        logger.info(f"  Total unique jobs fetched: {safe_len(unique_jobs)}")

        # ─── Step 4: Semantic search via ChromaDB ────────────
        logger.info("[4/5] Running semantic search (ChromaDB + sentence-transformers)")

        job_store = None
        self.last_vector_stats = {"total_jobs": 0}

        # 4a. Index fetched jobs into vector store (with duplicate check!)
        try:
            job_store = JobVectorStore()
            add_result = job_store.add_jobs(unique_jobs)
            self.last_vector_stats = job_store.get_stats()
            logger.info(f"  Vector DB: added {add_result['added']}, skipped {add_result['skipped']} duplicates")
            logger.info(f"  Vector DB total: {self.last_vector_stats['total_jobs']} jobs")
        except Exception as e:
            logger.warning(f"  Vector indexing failed: {e} — falling back to keyword search")

        # 4b. Run semantic search using resume text as query (⚡ FASTER!)
        semantic_results = []
        try:
            semantic_search = SemanticJobSearch()
            semantic_results = semantic_search.search(
                query=resume_text[:1000],  # ⚡ Less text = faster (was 2000)
                user_id=user_id,
                n_results=10,              # ⚡ Fewer results = faster (was 20)
                use_resume=False,          # ⚡ Skip user-specific (faster, was True)
                filter_remote=False
            )
            logger.info(f"  Semantic matches found: {safe_len(semantic_results)}")
        except Exception as e:
            logger.warning(f"  Semantic search failed: {e}")

        # 4c. Convert semantic results to AI-ranker format
        if semantic_results:
            jobs_for_ai_ranking = []
            for sem_job in semantic_results[:10]:  # ⚡ Top 10 (was 15)
                jobs_for_ai_ranking.append({
                    "title": sem_job.get("title", ""),
                    "company": sem_job.get("company", ""),
                    "url": sem_job.get("url", ""),
                    "location": sem_job.get("location", ""),
                    "description": sem_job.get("document", "")[:1000],
                    "semantic_score": sem_job.get("similarity_score", 0) * 100
                })
        else:
            # Fallback to first 10 fetched jobs
            jobs_for_ai_ranking = unique_jobs[:10]
            logger.info("  Using first 10 fetched jobs (no semantic results)")

        # ─── Step 5: AI ranking (Mistral) on top candidates ─
        logger.info("[5/5] AI ranking top candidates (Mistral)")
        # ⚡ Lower threshold = more jobs pass = less filtering time
        filtered_jobs = filter_jobs_with_ai(jobs_for_ai_ranking, profile, min_score=30)

        # 5a. Combine semantic + AI scores
        for job in filtered_jobs:
            sem_score = 0
            for s in semantic_results:
                if s.get("url") == job.get("url") or s.get("title") == job.get("title"):
                    sem_score = s.get("similarity_score", 0) * 100
                    break

            ai_score = job.get("score", 0) or job.get("match_score", 0)
            job["final_score"] = round(0.4 * sem_score + 0.6 * ai_score, 2)
            job["semantic_score"] = round(sem_score, 2)
            job["ai_score"] = ai_score

        # 5b. Sort by final combined score
        filtered_jobs.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        top_matches = filtered_jobs[:settings.TOP_MATCHES_COUNT]
        logger.info(f"  Final top matches: {safe_len(top_matches)}")

        # ─── Generate cover letters ───────────────────────────
        cover_letter_paths = []
        if self.generate_letters and top_matches:
            logger.info("Generating cover letters for top 3 matches...")
            letter_results = generate_cover_letters_for_top_matches(
                profile, top_matches, top_n=3
            )
            cover_letter_paths = [r["file_path"] for r in letter_results]

        # ─── Store resume in vector store (for future matches) ─
        if user_id is not None:
            try:
                resume_store = ResumeVectorStore()
                resume_store.add_resume(
                    user_id=user_id,
                    resume_text=resume_text,
                    skills=profile.get("skills", [])
                )
                logger.info(f"  Resume stored in vector DB for user {user_id}")
            except Exception as e:
                logger.warning(f"  Resume vector storage failed: {e}")

        # ─── Build final output ──────────────────────────────
        ranked_output = rank_jobs(top_matches, profile)

        results = {
            "profile": profile,
            "total_jobs_found": safe_len(unique_jobs),
            "top_matches_count": safe_len(top_matches),
            "ranked_matches": ranked_output,
            "cover_letters_generated": safe_len(cover_letter_paths),
            "jobs": top_matches,
            "all_jobs": unique_jobs,
            "semantic_search_used": safe_len(semantic_results) > 0,
            "vector_db_jobs": self.last_vector_stats.get("total_jobs", 0) if self.last_vector_stats else 0,
            "search_keywords_used": search_terms
        }

        save_results(results, settings.OUTPUT_FILE)
        logger.info(f"Results saved to {settings.OUTPUT_FILE}")

        return results


# ─── API-friendly function ──────────────────────────────────

def run_job_search(
    resume_path: str = None,           # ⚡ Optional now
    resume_text: str = "",             # ⚡ NEW!
    user_name: str = "User",
    generate_cover_letters: bool = False,
    location: str = None,
    top_n: int = None,
    user_id: int = None,
    custom_keywords: list = None
) -> dict:
    """
    Function-based interface used by the FastAPI layer.
    Wraps the JobFinderAgent and returns a clean dict for JSON response.
    
    ⚡ NEW: Accepts resume_text from DB (no PDF file needed!)
    """
    try:
        location = location or settings.DEFAULT_LOCATION
        top_n = top_n or settings.TOP_MATCHES_COUNT

        agent = JobFinderAgent(generate_letters=generate_cover_letters)
        if location:
            agent.location = location

        results = agent.run(
            resume_path=resume_path,
            resume_text=resume_text,  # ⚡ Pass through!
            candidate_name=user_name,
            user_id=user_id,
            custom_keywords=custom_keywords
        )

        # Normalize output for API
        return {
            "status": "success",
            "profile": {
                "name": results["profile"].get("name"),
                "skills": results["profile"].get("skills", []),
                "job_titles": results["profile"].get("job_titles", []),
                "resume_chars": safe_len(results["profile"].get("resume_text", ""))
            },
            "total_jobs_found": results.get("total_jobs_found", 0),
            "top_matches_count": results.get("top_matches_count", 0),
            "cover_letters_generated": results.get("cover_letters_generated", 0),
            "top_jobs": results.get("jobs", []),
            "ranked_matches": results.get("ranked_matches", []),
            "all_jobs": results.get("all_jobs", []),
            "semantic_search_used": results.get("semantic_search_used", False),
            "vector_db_jobs": results.get("vector_db_jobs", 0),
            "search_keywords_used": results.get("search_keywords_used", []),
            "location": location
        }

    except Exception as e:
        logger.error(f"run_job_search failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "profile": None,
            "top_jobs": [],
            "all_jobs": [],
            "total_jobs_found": 0,
            "top_matches_count": 0,
            "cover_letters_generated": 0,
            "semantic_search_used": False
        }


def cli_main():
    """Original CLI entrypoint used by main.py."""
    from pathlib import Path

    print("\n" + "=" * 60)
    print(" AI JOB FINDER AGENT")
    print(f" {settings.DEFAULT_LOCATION}, Pakistan")
    print("=" * 60 + "\n")

    resume_path = input("Enter path to your resume PDF: ").strip()
    user_name = input("Enter your name: ").strip()
    cover_letters_input = input("Generate cover letters for top 3 matches? (y/n): ").strip().lower()
    generate_letters = cover_letters_input == "y"

    if resume_path and not Path(resume_path).exists():
        for alt in [f"data/resumes/{resume_path}", f"./{resume_path}"]:
            if Path(alt).exists():
                resume_path = alt
                break

    results = run_job_search(
        resume_path=resume_path,
        user_name=user_name,
        generate_cover_letters=generate_letters
    )

    if results["status"] == "success":
        print("\n" + "=" * 60)
        print(" TOP JOB MATCHES (Semantic + AI Ranked)")
        print("=" * 60 + "\n")

        if results.get("semantic_search_used"):
            print(f"✅ Semantic search used ({results.get('vector_db_jobs', 0)} jobs in vector DB)\n")

        for i, job in enumerate(results["top_jobs"][:10], 1):
            print(f"\n{i}. {job.get('title')} at {job.get('company')}")
            final = job.get("final_score") or job.get("score") or job.get("match_score")
            sem = job.get("semantic_score", 0)
            ai = job.get("ai_score", 0)
            print(f"   Final Score: {final}/100  (Semantic: {sem:.1f} + AI: {ai})")
            print(f"   Location: {job.get('location', 'N/A')}")
            print(f"   URL: {job.get('url')}")

        print("\n" + "=" * 60)
        print(" SUMMARY")
        print("=" * 60)
        print(f" Jobs fetched: {results['total_jobs_found']}")
        print(f" Top matches: {results['top_matches_count']}")
        print(f" Cover letters: {results['cover_letters_generated']}")
        if results.get("semantic_search_used"):
            print(f" Vector DB jobs: {results.get('vector_db_jobs', 0)}")
    else:
        print(f"\n Error: {results['error']}")


if __name__ == "__main__":
    cli_main()