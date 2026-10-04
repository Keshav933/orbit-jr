import sys
from pathlib import Path
from collections import Counter

# Add project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import get_connection


LIVE_SOURCE_TYPES = (
    "jobicy",
    "himalayas",
    "remoteok",
)

SAMPLE_JOBS_PER_SOURCE = 5
MAX_SKILLS_PER_JOB = 30


def print_section(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def get_live_jobs(cursor):
    placeholders = ", ".join(["%s"] * len(LIVE_SOURCE_TYPES))

    cursor.execute(
        f"""
        SELECT
            id,
            source_type,
            title,
            company_name
        FROM jobs
        WHERE source_type IN ({placeholders})
        ORDER BY source_type, id DESC
        """,
        LIVE_SOURCE_TYPES,
    )

    return cursor.fetchall()


def get_job_skills(cursor, job_id):
    cursor.execute(
        """
        SELECT
            s.name AS skill_name,
            js.importance,
            js.requirement_type
        FROM job_skills js
        INNER JOIN skills s
            ON s.id = js.skill_id
        WHERE js.job_id = %s
        ORDER BY js.importance DESC, s.name
        """,
        (job_id,),
    )

    return cursor.fetchall()


def inspect():
    print("ORBIT-JR LIVE JOB SKILL QUALITY INSPECTION")
    print("=" * 100)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        jobs = get_live_jobs(cursor)

        if not jobs:
            print("No live jobs found.")
            return

        print_section("LIVE JOB SUMMARY")

        source_counts = Counter(
            row[1] for row in jobs
        )

        print("Total live jobs:", len(jobs))

        for source_type in LIVE_SOURCE_TYPES:
            print(
                f"{source_type:12}: "
                f"{source_counts.get(source_type, 0)}"
            )

        # Collect statistics over all live job mappings.
        total_mappings = 0
        jobs_with_skills = 0
        requirement_counts = Counter()
        importance_counts = Counter()
        skill_frequency = Counter()

        for job_id, source_type, title, company_name in jobs:
            skills = get_job_skills(cursor, job_id)

            if skills:
                jobs_with_skills += 1

            for skill_name, importance, requirement_type in skills:
                total_mappings += 1
                skill_frequency[skill_name] += 1
                requirement_counts[
                    requirement_type or "NULL"
                ] += 1

                importance_value = (
                    float(importance)
                    if importance is not None
                    else 0.0
                )

                importance_counts[
                    f"{importance_value:.2f}"
                ] += 1

        print_section("MAPPING STATISTICS")

        print("Jobs with skills:", jobs_with_skills)
        print(
            "Jobs without skills:",
            len(jobs) - jobs_with_skills,
        )
        print("Total job-skill mappings:", total_mappings)

        if jobs:
            average = total_mappings / len(jobs)
            print(
                "Average skills per live job:",
                f"{average:.2f}",
            )

        print("\nRequirement types:")

        for key, value in sorted(
            requirement_counts.items()
        ):
            print(f"  {key}: {value}")

        print("\nImportance values:")

        for key, value in sorted(
            importance_counts.items()
        ):
            print(f"  {key}: {value}")

        print_section("MOST FREQUENT EXTRACTED SKILLS")

        if not skill_frequency:
            print("No skill mappings found.")
        else:
            for skill_name, count in skill_frequency.most_common(30):
                print(
                    f"{count:4}  {skill_name}"
                )

        print_section("SAMPLE JOB SKILL DETAILS")

        # Pick a few recent jobs from each source.
        for source_type in LIVE_SOURCE_TYPES:
            source_jobs = [
                job
                for job in jobs
                if job[1] == source_type
            ][:SAMPLE_JOBS_PER_SOURCE]

            print(f"\nSOURCE: {source_type.upper()}")

            if not source_jobs:
                print("No jobs found.")
                continue

            for job_id, source, title, company_name in source_jobs:
                skills = get_job_skills(
                    cursor,
                    job_id,
                )

                print()
                print(
                    f"JOB ID      : {job_id}"
                )
                print(
                    f"COMPANY     : {company_name or 'N/A'}"
                )
                print(
                    f"TITLE       : {title or 'N/A'}"
                )
                print(
                    f"SKILL COUNT : {len(skills)}"
                )

                if not skills:
                    print("SKILLS      : None")
                    continue

                print("SKILLS:")

                for skill_name, importance, requirement_type in skills[
                    :MAX_SKILLS_PER_JOB
                ]:
                    print(
                        f"  - {skill_name} | "
                        f"importance={importance} | "
                        f"type={requirement_type}"
                    )

                if len(skills) > MAX_SKILLS_PER_JOB:
                    print(
                        f"  ... {len(skills) - MAX_SKILLS_PER_JOB} "
                        "more skills"
                    )

        print_section("QUALITY CHECKS")

        suspicious_terms = {
            "analysis",
            "application",
            "communication",
            "development",
            "experience",
            "knowledge",
            "management",
            "process",
            "project",
            "service",
            "skills",
            "software",
            "system",
            "technology",
            "testing",
            "work",
        }

        suspicious_matches = []

        for skill_name, count in skill_frequency.items():
            normalized = skill_name.strip().lower()

            if normalized in suspicious_terms:
                suspicious_matches.append(
                    (skill_name, count)
                )

        if suspicious_matches:
            print(
                "Potentially generic skill names detected:"
            )

            for skill_name, count in sorted(
                suspicious_matches,
                key=lambda item: (-item[1], item[0].lower()),
            ):
                print(
                    f"  - {skill_name}: {count} mappings"
                )
        else:
            print(
                "No known generic single-word terms "
                "were found in live job mappings."
            )

        print()
        print(
            "Note: this script checks mapping data only. "
            "It does not modify jobs, skills, or job_skills."
        )

        print_section("INSPECTION COMPLETED")

    except Exception as error:
        print_section("INSPECTION FAILED")
        print("Error type:", type(error).__name__)
        print("Error:", error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    inspect()

