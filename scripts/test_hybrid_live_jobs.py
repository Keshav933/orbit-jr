import sys
from pathlib import Path
from collections import Counter

# Add project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.hybrid_retrieval import retrieve_hybrid_jobs


PROFILE_ID = 1
TOP_K = 20

LIVE_JOB_MIN_ID = 2477


def main():
    print("ORBIT-JR HYBRID RETRIEVAL TEST")
    print("=" * 100)
    print("Profile ID:", PROFILE_ID)
    print("Top K:", TOP_K)

    try:
        results = retrieve_hybrid_jobs(
            PROFILE_ID,
            top_k=TOP_K,
        )

        print()
        print("Results returned:", len(results))

        if not results:
            print()
            print("No hybrid results were returned.")
            return

        live_results = [
            result
            for result in results
            if result["job_id"] >= LIVE_JOB_MIN_ID
        ]

        role_radar_results = [
            result
            for result in results
            if result["job_id"] < LIVE_JOB_MIN_ID
        ]

        print()
        print("SOURCE RANGE CHECK")
        print(
            "Live-source results:",
            len(live_results),
        )
        print(
            "Role Radar results:",
            len(role_radar_results),
        )

        print()
        print("-" * 100)
        print(
            f"{'RANK':<6}"
            f"{'JOB ID':<9}"
            f"{'SOURCE':<12}"
            f"{'HYBRID':<10}"
            f"{'LEXICAL':<10}"
            f"{'SEMANTIC':<10}"
            f"{'SKILLS':<8}"
            f"TITLE"
        )
        print("-" * 100)

        for rank, result in enumerate(
            results,
            start=1,
        ):
            job_id = result["job_id"]

            if job_id >= LIVE_JOB_MIN_ID:
                source = "LIVE"
            else:
                source = "ROLE-RADAR"

            print(
                f"{rank:<6}"
                f"{job_id:<9}"
                f"{source:<12}"
                f"{result['hybrid_score']:<10}"
                f"{result['lexical_score']:<10}"
                f"{result['semantic_score']:<10}"
                f"{result['matched_skill_count']:<8}"
                f"{result['title']}"
            )

        print()
        print("-" * 100)
        print("LIVE JOB DETAILS")
        print("-" * 100)

        if not live_results:
            print("No live jobs appeared in the top results.")
        else:
            for rank, result in enumerate(
                results,
                start=1,
            ):
                if result["job_id"] < LIVE_JOB_MIN_ID:
                    continue

                print()
                print("Rank:", rank)
                print("Job ID:", result["job_id"])
                print("Title:", result["title"])
                print("Company:", result["company_name"])
                print("Location:", result["location"])
                print("Hybrid score:", result["hybrid_score"])
                print("Lexical score:", result["lexical_score"])
                print("Semantic score:", result["semantic_score"])
                print(
                    "Matched skills:",
                    result["matched_skill_count"],
                )
                print(
                    "Total job skills:",
                    result["total_job_skills"],
                )

                matched_skills = result.get(
                    "matched_skills",
                    [],
                )

                if matched_skills:
                    print("Matched skill names:")

                    for skill in matched_skills:
                        print(
                            "  -",
                            skill["skill_name"],
                        )

        print()
        print("-" * 100)
        print("VALIDATION")
        print("-" * 100)

        if live_results:
            print(
                "PASS: Live jobs are participating "
                "in hybrid retrieval."
            )
        else:
            print(
                "CHECK NEEDED: No live jobs appeared "
                "in the top results."
            )

        # Verify that any returned live job has a semantic score
        # coming from the combined FAISS index.
        live_without_semantic = [
            result
            for result in live_results
            if result["semantic_score"] == 0.0
        ]

        if live_results and not live_without_semantic:
            print(
                "PASS: Returned live jobs have "
                "non-zero semantic scores."
            )
        elif live_without_semantic:
            print(
                "WARNING: Some live jobs have semantic_score=0.0."
            )

        # Check that every result has at least one lexical skill match.
        zero_skill_results = [
            result
            for result in results
            if result["matched_skill_count"] <= 0
        ]

        if not zero_skill_results:
            print(
                "PASS: Every returned result has "
                "at least one matched skill."
            )
        else:
            print(
                "FAIL: Some results have zero "
                "matched skills."
            )

        # Show score ranges for quick validation.
        print()
        print("SCORE RANGES")

        hybrid_values = [
            result["hybrid_score"]
            for result in results
        ]

        semantic_values = [
            result["semantic_score"]
            for result in results
        ]

        lexical_values = [
            result["lexical_score"]
            for result in results
        ]

        print(
            "Hybrid:",
            min(hybrid_values),
            "to",
            max(hybrid_values),
        )
        print(
            "Lexical:",
            min(lexical_values),
            "to",
            max(lexical_values),
        )
        print(
            "Semantic:",
            min(semantic_values),
            "to",
            max(semantic_values),
        )

        print()
        print("=" * 100)
        print("HYBRID RETRIEVAL TEST COMPLETED")
        print("=" * 100)

    except Exception as error:
        print()
        print("=" * 100)
        print("HYBRID RETRIEVAL TEST FAILED")
        print("=" * 100)
        print("Error type:", type(error).__name__)
        print("Error:", error)


if __name__ == "__main__":
    main()
