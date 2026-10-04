import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.ranking import rank_jobs


PROFILE_ID = 1


results = rank_jobs(
    PROFILE_ID,
    retrieval_k=50,
    top_k=10,
)


print()
print("Market-aware ranked jobs")
print("=" * 80)

if not results:
    print("No ranked jobs found.")
else:

    for index, job in enumerate(
        results,
        start=1,
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
            f"   Hybrid score: "
            f"{job['hybrid_score']:.4f}"
        )

        print(
            f"   Skill coverage: "
            f"{job['skill_coverage']:.4f}"
        )

        print(
            f"   Experience score: "
            f"{job['experience_score']:.4f}"
        )

        print(
            f"   Role score: "
            f"{job['role_score']:.4f}"
        )

        print(
            f"   Seniority score: "
            f"{job['seniority_score']:.4f}"
        )

        print(
            f"   Location score: "
            f"{job['location_score']:.4f}"
        )

        print(
            f"   Market score: "
            f"{job['market_score']:.4f}"
        )

        print(
            f"   FINAL SCORE: "
            f"{job['final_score']:.4f}"
        )

        print(
            f"   Matched skills: "
            f"{job['matched_skill_count']}"
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