import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.semantic_retrieval import (
    semantic_search
)


PROFILE_ID = 1


results = semantic_search(
    PROFILE_ID,
    top_k=10,
)

print()
print("Top semantic job recommendations")
print("=" * 70)

if not results:
    print("No semantic results found.")
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
            f"   Semantic score: "
            f"{job['semantic_score']:.4f}"
        )
        print(
            f"   URL: {job['source_url']}"
        )