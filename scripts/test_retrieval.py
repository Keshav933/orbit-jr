import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.retrieval import retrieve_jobs


PROFILE_ID = 1


results = retrieve_jobs(
    PROFILE_ID,
    top_k=10,
)

print()
print("Top recommended jobs")
print("=" * 70)

if not results:
    print("No matching jobs found.")
else:
    for index, job in enumerate(
        results,
        start=1
    ):
        print()
        print(f"{index}. {job['title']}")
        print(
            f"   Company: {job['company_name']}"
        )
        print(
            f"   Location: {job['location']}"
        )
        print(
            f"   Match score: "
            f"{job['match_score']:.4f}"
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
                f"      - {skill['skill_name']}"
            )

        print(
            f"   URL: {job['source_url']}"
        )