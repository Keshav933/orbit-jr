import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.hybrid_retrieval import (
    retrieve_hybrid_jobs
)


PROFILE_ID = 1


results = retrieve_hybrid_jobs(
    PROFILE_ID,
    top_k=10,
)


print()
print("Top hybrid job recommendations")
print("=" * 75)

if not results:
    print("No hybrid results found.")
else:
    for index, job in enumerate(
        results,
        start=1
    ):
        print()
        print(
            f"{index}. {job['title']}"
        )

        print(
            f"   Company: "
            f"{job['company_name']}"
        )

        print(
            f"   Location: "
            f"{job['location']}"
        )

        print(
            f"   Lexical score: "
            f"{job['lexical_score']:.4f}"
        )

        print(
            f"   Semantic score: "
            f"{job['semantic_score']:.4f}"
        )

        print(
            f"   Hybrid score: "
            f"{job['hybrid_score']:.4f}"
        )

        print(
            f"   Matched skills: "
            f"{job['matched_skill_count']}"
        )

        print(
            f"   Total job skills: "
            f"{job['total_job_skills']}"
        )

        print("   Skills:")

        for skill in job["matched_skills"]:
            print(
                f"      - "
                f"{skill['skill_name']}"
            )

        print(
            f"   URL: {job['source_url']}"
        )