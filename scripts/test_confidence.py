import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.confidence import (
    get_ranked_jobs_with_confidence,
)


PROFILE_ID = 1


results = get_ranked_jobs_with_confidence(
    PROFILE_ID,
    retrieval_k=50,
    top_k=10,
)


print()
print("Ranked jobs with confidence")
print("=" * 85)


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
            f"   Evidence coverage: "
            f"{job['evidence_coverage']:.4f}"
        )

        print(
            f"   Skill coverage: "
            f"{job['skill_coverage']:.4f}"
        )

        print(
            f"   Confidence: "
            f"{job['confidence']:.4f}"
        )

        print(
            f"   Confidence label: "
            f"{job['confidence_label']}"
        )

        print(
            f"   Required gaps: "
            f"{len(job['required_gaps'])}"
        )

        print(
            f"   Preferred gaps: "
            f"{len(job['preferred_gaps'])}"
        )