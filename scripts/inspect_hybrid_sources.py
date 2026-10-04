import sys
from pathlib import Path

# Add project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.hybrid_retrieval import (
    calculate_lexical_scores,
    get_job_skills,
    get_profile_skills,
    load_index_and_metadata,
    load_model,
    create_profile_text,
    convert_cosine_to_zero_one,
)


PROFILE_ID = 1

LIVE_SOURCE_MIN_ID = 2477

LIVE_SOURCE_TYPES = {
    "jobicy",
    "himalayas",
    "remoteok",
}


def main():
    print("ORBIT-JR HYBRID SOURCE INSPECTION")
    print("=" * 110)
    print("Profile ID:", PROFILE_ID)

    try:
        # ---------------------------------------------------------
        # 1. Load candidate skills.
        # ---------------------------------------------------------
        profile_skills = get_profile_skills(
            PROFILE_ID
        )

        if not profile_skills:
            print("No profile skills found.")
            return

        profile_skill_ids = {
            skill["skill_id"]
            for skill in profile_skills
        }

        print(
            "Profile skills:",
            len(profile_skills),
        )

        # ---------------------------------------------------------
        # 2. Load all Role Radar + live job-skill rows.
        # ---------------------------------------------------------
        job_rows = get_job_skills()

        if not job_rows:
            print("No job-skill rows found.")
            return

        lexical_results = calculate_lexical_scores(
            profile_skill_ids,
            job_rows,
        )

        # ---------------------------------------------------------
        # 3. Load combined semantic index.
        # ---------------------------------------------------------
        index, metadata = load_index_and_metadata()

        print(
            "FAISS jobs indexed:",
            index.ntotal,
        )
        print(
            "Metadata records:",
            len(metadata),
        )

        # ---------------------------------------------------------
        # 4. Create semantic query.
        # ---------------------------------------------------------
        profile_text = create_profile_text(
            profile_skills
        )

        model = load_model()

        query_embedding = model.encode(
            [profile_text],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        scores, indices = index.search(
            query_embedding,
            index.ntotal,
        )

        semantic_scores = {}

        for score, index_position in zip(
            scores[0],
            indices[0],
        ):
            if index_position < 0:
                continue

            job = metadata[
                int(index_position)
            ]

            semantic_scores[
                job["job_id"]
            ] = convert_cosine_to_zero_one(
                score
            )

        # ---------------------------------------------------------
        # 5. Build complete hybrid candidate set.
        # ---------------------------------------------------------
        combined_results = []

        for job_id, job in lexical_results.items():

            semantic_score = semantic_scores.get(
                job_id,
                0.0,
            )

            hybrid_score = (
                0.5 * job["lexical_score"]
                + 0.5 * semantic_score
            )

            # Match the actual hybrid retrieval rule.
            if len(job["matched_skills"]) <= 0:
                continue

            combined_results.append(
                {
                    "job_id": job_id,
                    "title": job["title"],
                    "company_name": job["company_name"],
                    "location": job["location"],
                    "source_url": job["source_url"],
                    "lexical_score": job["lexical_score"],
                    "semantic_score": semantic_score,
                    "hybrid_score": hybrid_score,
                    "matched_skill_count": len(
                        job["matched_skills"]
                    ),
                    "total_job_skills": job[
                        "total_job_skills"
                    ],
                    "matched_skills": job[
                        "matched_skills"
                    ],
                }
            )

        combined_results.sort(
            key=lambda item: item["hybrid_score"],
            reverse=True,
        )

        print()
        print("-" * 110)
        print("COMPLETE HYBRID CANDIDATE SET")
        print("-" * 110)
        print(
            "Candidates with at least one lexical skill:",
            len(combined_results),
        )

        # ---------------------------------------------------------
        # 6. Classify source using the job ID range for the
        # current database, then separately verify source_type
        # directly from MySQL.
        # ---------------------------------------------------------
        from backend.app.database import get_connection

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            live_placeholders = ", ".join(
                ["%s"] * len(LIVE_SOURCE_TYPES)
            )

            cursor.execute(
                f"""
                SELECT
                    id,
                    source,
                    source_type
                FROM jobs
                WHERE source = 'role-radar'
                   OR (
                        source_type IN ({live_placeholders})
                        AND is_active = 1
                   )
                """,
                tuple(LIVE_SOURCE_TYPES),
            )

            source_rows = cursor.fetchall()

        finally:
            cursor.close()
            connection.close()

        source_map = {
            row["id"]: (
                "LIVE"
                if row["source_type"] in LIVE_SOURCE_TYPES
                else "ROLE-RADAR"
            )
            for row in source_rows
        }

        live_candidates = [
            result
            for result in combined_results
            if source_map.get(result["job_id"]) == "LIVE"
        ]

        role_radar_candidates = [
            result
            for result in combined_results
            if source_map.get(result["job_id"]) == "ROLE-RADAR"
        ]

        print()
        print("SOURCE COUNTS")
        print(
            "Role Radar candidates:",
            len(role_radar_candidates),
        )
        print(
            "Live candidates:",
            len(live_candidates),
        )

        # ---------------------------------------------------------
        # 7. Show the highest-ranked live candidates.
        # ---------------------------------------------------------
        print()
        print("-" * 110)
        print("HIGHEST-RANKED LIVE JOBS")
        print("-" * 110)

        if not live_candidates:
            print(
                "NO LIVE JOBS ENTERED THE HYBRID CANDIDATE SET."
            )
        else:
            for result in live_candidates[:30]:
                rank = (
                    combined_results.index(result) + 1
                )

                print()
                print("Hybrid rank:", rank)
                print("Job ID:", result["job_id"])
                print("Title:", result["title"])
                print("Company:", result["company_name"])
                print("Location:", result["location"])
                print(
                    "Lexical:",
                    round(
                        result["lexical_score"],
                        4,
                    ),
                )
                print(
                    "Semantic:",
                    round(
                        result["semantic_score"],
                        4,
                    ),
                )
                print(
                    "Hybrid:",
                    round(
                        result["hybrid_score"],
                        4,
                    ),
                )
                print(
                    "Matched skills:",
                    result["matched_skill_count"],
                )
                print(
                    "Total job skills:",
                    result["total_job_skills"],
                )

                print("Matched skill names:")

                for skill in result["matched_skills"]:
                    print(
                        "  -",
                        skill["skill_name"],
                    )

        # ---------------------------------------------------------
        # 8. Show source distribution among the top 100.
        # ---------------------------------------------------------
        print()
        print("-" * 110)
        print("TOP 100 SOURCE DISTRIBUTION")
        print("-" * 110)

        top_100 = combined_results[:100]

        top_100_live = [
            result
            for result in top_100
            if source_map.get(result["job_id"]) == "LIVE"
        ]

        top_100_role_radar = [
            result
            for result in top_100
            if source_map.get(result["job_id"]) == "ROLE-RADAR"
        ]

        print(
            "Top 100 Role Radar:",
            len(top_100_role_radar),
        )
        print(
            "Top 100 live:",
            len(top_100_live),
        )

        # ---------------------------------------------------------
        # 9. Check whether every live candidate has a semantic
        # score from the combined index.
        # ---------------------------------------------------------
        print()
        print("-" * 110)
        print("LIVE SEMANTIC INDEX VALIDATION")
        print("-" * 110)

        zero_semantic = [
            result
            for result in live_candidates
            if result["semantic_score"] == 0.0
        ]

        if live_candidates and not zero_semantic:
            print(
                "PASS: All live candidates have "
                "non-zero semantic scores."
            )
        elif zero_semantic:
            print(
                "WARNING:",
                len(zero_semantic),
                "live candidates have semantic_score=0.0.",
            )
        else:
            print(
                "No live candidates were available "
                "for semantic validation."
            )

        # ---------------------------------------------------------
        # 10. Final conclusion.
        # ---------------------------------------------------------
        print()
        print("=" * 110)

        if live_candidates:
            print(
                "RESULT: LIVE JOBS ARE ENTERING HYBRID RETRIEVAL."
            )
            print(
                "They may simply be below the requested top_k "
                "used by the normal recommendation endpoint."
            )
        else:
            print(
                "RESULT: LIVE JOBS ARE NOT ENTERING "
                "THE HYBRID CANDIDATE SET."
            )

        print("=" * 110)
        print("INSPECTION COMPLETED")

    except Exception as error:
        print()
        print("=" * 110)
        print("INSPECTION FAILED")
        print("=" * 110)
        print("Error type:", type(error).__name__)
        print("Error:", error)


if __name__ == "__main__":
    main()
