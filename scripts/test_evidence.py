import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.evidence import (
    get_ranked_jobs_with_explanations
)


PROFILE_ID = 1


results = get_ranked_jobs_with_explanations(
    PROFILE_ID,
    retrieval_k=50,
    top_k=5,
)


print()
print("Ranked jobs with evidence and skill gaps")
print("=" * 80)


if not results:
    print("No results found.")
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
            f"   Final score: "
            f"{job['final_score']:.4f}"
        )

        print(
            f"   Skill coverage: "
            f"{job['skill_coverage']:.4f}"
        )

        print()
        print("   MATCHED SKILLS:")

        if job["matched_skills"]:

            for skill in job[
                "matched_skills"
            ]:
                print(
                    f"      + "
                    f"{skill['skill_name']}"
                )

        else:
            print("      None")

        print()
        print("   REQUIRED GAPS:")

        if job["required_gaps"]:

            for skill in job[
                "required_gaps"
            ]:
                print(
                    f"      - "
                    f"{skill['skill_name']}"
                )

        else:
            print(
                "      None"
            )

        print()
        print("   PREFERRED GAPS:")

        if job["preferred_gaps"]:

            for skill in job[
                "preferred_gaps"
            ]:
                print(
                    f"      - "
                    f"{skill['skill_name']}"
                )

        else:
            print(
                "      None"
            )

        print()
        print(
            f"   Evidence count: "
            f"{job['evidence_count']}"
        )

        print("   EVIDENCE:")

        if job["evidence"]:

            for item in job["evidence"]:

                print(
                    f"      {item['skill_name']}:"
                )

                print(
                    f"         "
                    f"{item['evidence_text']}"
                )

        else:
            print(
                "      No evidence found."
            )

        print()
        print(
            f"   URL: {job['source_url']}"
        )