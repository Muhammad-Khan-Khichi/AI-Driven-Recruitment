import os
import sys
from agent import JobFinderAgent
from utils import get_logger

logger = get_logger(__name__)


def main():
    print("\n" + "="*60)
    print(" AI JOB FINDER AGENT")
    print(" Lahore, Pakistan • Indeed • LinkedIn")
    print("="*60 + "\n")

    resume_path = input("Enter path to your resume PDF: ").strip()
    if not os.path.exists(resume_path):
        print(f"❌ File not found: {resume_path}")
        sys.exit(1)

    candidate_name = input("Enter your name: ").strip() or "Candidate"
    generate_letters = input("Generate cover letters for top 3 matches? (y/n): ").strip().lower() == "y"

    try:
        agent = JobFinderAgent(generate_letters=generate_letters)
        results = agent.run(resume_path, candidate_name)

        print("\n" + "="*60)
        print(" TOP JOB MATCHES")
        print("="*60 + "\n")
        print(results["ranked_matches"])

        print("\n" + "="*60)
        print(" SUMMARY")
        print("="*60)
        print(f" Jobs analyzed:   {results['total_jobs_found']}")
        print(f" Top matches:    {results['top_matches_count']}")
        print(f" Cover letters:  {results['cover_letters_generated']}")
        print(f" Results saved:  outputs/results.json")
        print(f" Letters saved:  data/cover_letters/")
        print("="*60)

    except Exception as e:
        logger.error(f"Agent failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()