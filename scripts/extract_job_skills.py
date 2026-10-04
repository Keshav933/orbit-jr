import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.database import get_connection
from backend.app.skill_extractor import extract_skills_from_text


REQUIRED_WORDS = (
    "required",
    "must have",
    "must",
    "mandatory",
    "essential",
    "need",
    "needs",
)

PREFERRED_WORDS = (
    "preferred",
    "nice to have",
    "plus",
    "bonus",
    "desirable",
)


def classify_requirement(job_text, matched_aliases):
    text = job_text.lower()

    best_type = "required"

    for alias in matched_aliases:
        alias = alias.lower()

        start = 0

        while True:
            position = text.find(alias, start)

            if position == -1:
                break

            # Look around the skill mention.
            window_start = max(0, position - 100)
            window_end = min(
                len(text),
                position + len(alias) + 100
            )

            context = text[window_start:window_end]

            if any(word in context for word in PREFERRED_WORDS):
                best_type = "preferred"

            if any(word in context for word in REQUIRED_WORDS):
                return "required"

            start = position + len(alias)

    return best_type


def calculate_importance(job_title, skill):
    title = job_title.lower()

    for alias in skill["matched_aliases"]:
        if alias.lower() in title:
            return 2.00

    return 1.00


def main():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Get Role Radar jobs.
        cursor.execute("""
            SELECT
                id,
                title,
                description
            FROM jobs
            WHERE source = 'role-radar'
            ORDER BY id
        """)

        jobs = cursor.fetchall()

        if not jobs:
            print("No Role Radar jobs found in the database.")
            return

        print(f"Role Radar jobs found: {len(jobs)}")

        # Allow the script to be safely rerun.
        cursor.execute("""
            DELETE js
            FROM job_skills js
            JOIN jobs j
                ON j.id = js.job_id
            WHERE j.source = 'role-radar'
        """)

        total_skills = 0
        jobs_with_skills = 0

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

                importance = calculate_importance(
                    title,
                    skill
                )

                requirement_type = classify_requirement(
                    job_text,
                    skill["matched_aliases"]
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
                    )
                )

                total_skills += 1

            # Commit in small batches.
            if index % 100 == 0:
                connection.commit()
                print(f"Processed {index}/{len(jobs)} jobs")

        connection.commit()

        print()
        print("Job skill extraction completed.")
        print(f"Jobs processed: {len(jobs)}")
        print(f"Jobs with detected skills: {jobs_with_skills}")
        print(f"Total job-skill mappings: {total_skills}")

    except Exception as error:
        connection.rollback()
        print("Job skill extraction failed.")
        print(error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()