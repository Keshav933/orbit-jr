import sys
from pathlib import Path

# Add project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import get_connection
from backend.app.skill_extractor import extract_skills_from_text

# Reuse the same requirement and importance rules
# already used by the Role Radar extraction script.
from scripts.extract_job_skills import (
    calculate_importance,
    classify_requirement,
)


LIVE_SOURCE_TYPES = (
    "jobicy",
    "himalayas",
    "remoteok",
)


def main():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        print("ORBIT-JR LIVE JOB SKILL EXTRACTION")
        print("=" * 80)

        placeholders = ", ".join(
            ["%s"] * len(LIVE_SOURCE_TYPES)
        )

        # Get only jobs imported from the live sources.
        cursor.execute(
            f"""
            SELECT
                id,
                title,
                description,
                source_type
            FROM jobs
            WHERE source_type IN ({placeholders})
            ORDER BY id
            """,
            LIVE_SOURCE_TYPES,
        )

        jobs = cursor.fetchall()

        if not jobs:
            print("No live jobs found in the database.")
            return

        print(f"Live jobs found: {len(jobs)}")

        # Show the current live-job distribution.
        source_counts = {}

        for job in jobs:
            source_type = job["source_type"] or "unknown"
            source_counts[source_type] = (
                source_counts.get(source_type, 0) + 1
            )

        print()
        print("Live jobs by source:")

        for source_type in sorted(source_counts):
            print(
                f"  {source_type}: "
                f"{source_counts[source_type]}"
            )

        # Safely rebuild mappings only for live jobs.
        # Role Radar job_skills remain untouched.
        cursor.execute(
            f"""
            DELETE js
            FROM job_skills js
            INNER JOIN jobs j
                ON j.id = js.job_id
            WHERE j.source_type IN ({placeholders})
            """,
            LIVE_SOURCE_TYPES,
        )

        deleted_mappings = cursor.rowcount

        print()
        print(
            "Previous live job-skill mappings deleted:",
            deleted_mappings,
        )

        total_skills = 0
        jobs_with_skills = 0
        source_skill_counts = {
            source_type: 0
            for source_type in LIVE_SOURCE_TYPES
        }

        for index, job in enumerate(jobs, start=1):

            title = job["title"] or ""
            description = job["description"] or ""

            job_text = f"{title}\n{description}"

            detected_skills = extract_skills_from_text(
                job_text
            )

            if detected_skills:
                jobs_with_skills += 1

            for skill in detected_skills:

                # Reuse the same importance calculation
                # as the existing Role Radar pipeline.
                importance = calculate_importance(
                    title,
                    skill,
                )

                # Reuse the same required/preferred
                # classification rules.
                requirement_type = classify_requirement(
                    job_text,
                    skill["matched_aliases"],
                )

                cursor.execute(
                    """
                    INSERT INTO job_skills
                    (
                        job_id,
                        skill_id,
                        importance,
                        requirement_type
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        job["id"],
                        skill["skill_id"],
                        importance,
                        requirement_type,
                    ),
                )

                total_skills += 1

                source_type = job["source_type"]

                if source_type in source_skill_counts:
                    source_skill_counts[source_type] += 1

            # Commit in small batches.
            if index % 100 == 0:
                connection.commit()
                print(
                    f"Processed {index}/{len(jobs)} jobs"
                )

        connection.commit()

        print()
        print("=" * 80)
        print("LIVE JOB SKILL EXTRACTION COMPLETED")
        print("=" * 80)
        print("Jobs processed:", len(jobs))
        print("Jobs with detected skills:", jobs_with_skills)
        print(
            "Jobs without detected skills:",
            len(jobs) - jobs_with_skills,
        )
        print("Total job-skill mappings:", total_skills)

        print()
        print("Mappings by source:")

        for source_type in sorted(source_skill_counts):
            print(
                f"  {source_type}: "
                f"{source_skill_counts[source_type]}"
            )

    except Exception as error:
        connection.rollback()

        print()
        print("=" * 80)
        print("LIVE JOB SKILL EXTRACTION FAILED")
        print("=" * 80)
        print("Error type:", type(error).__name__)
        print("Error:", error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
