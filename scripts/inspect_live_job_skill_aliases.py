import sys
from pathlib import Path

# Add project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import get_connection
from backend.app.skill_extractor import extract_skills_from_text


LIVE_SOURCE_TYPES = (
    "jobicy",
    "himalayas",
    "remoteok",
)

# These are examples that appeared suspicious in the previous
# live-job quality inspection. The script also prints every
# matched alias for the sampled jobs, so new suspicious cases
# can be identified from the output.
SUSPICIOUS_SKILL_NAMES = {
    "dies",
    "politics",
    "pregnancy",
    "history",
    "morality",
    "crafting",
    "rhetoric",
    "trademarks",
    "reverse engineering",
    "computer technology",
    "service-oriented modelling",
    "perform cleaning duties",
    "source (digital game creation systems)",
}


def print_section(title):
    print("\n" + "=" * 110)
    print(title)
    print("=" * 110)


def get_sample_jobs(cursor):
    placeholders = ", ".join(
        ["%s"] * len(LIVE_SOURCE_TYPES)
    )

    cursor.execute(
        f"""
        SELECT
            id,
            source_type,
            title,
            company_name,
            description
        FROM jobs
        WHERE source_type IN ({placeholders})
        ORDER BY id DESC
        """,
        LIVE_SOURCE_TYPES,
    )

    return cursor.fetchall()


def inspect():
    print("ORBIT-JR LIVE JOB SKILL ALIAS INSPECTION")
    print("=" * 110)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        jobs = get_sample_jobs(cursor)

        if not jobs:
            print("No live jobs found.")
            return

        suspicious_found = 0

        # Analyze all live jobs, but display only suspicious
        # mappings plus a compact sample of normal technical ones.
        for job_id, source_type, title, company_name, description in jobs:

            job_text = f"{title or ''}\n{description or ''}"

            detected_skills = extract_skills_from_text(
                job_text
            )

            for skill in detected_skills:

                skill_name = skill["skill_name"]
                skill_name_lower = skill_name.strip().lower()

                if skill_name_lower not in SUSPICIOUS_SKILL_NAMES:
                    continue

                suspicious_found += 1

                print_section(
                    f"SUSPICIOUS MAPPING #{suspicious_found}"
                )

                print("Job ID          :", job_id)
                print("Source          :", source_type)
                print("Company         :", company_name or "N/A")
                print("Job title       :", title or "N/A")
                print("Skill           :", skill_name)
                print(
                    "Importance      :",
                    "2.00"
                    if any(
                        alias.lower() in (title or "").lower()
                        for alias in skill["matched_aliases"]
                    )
                    else "1.00",
                )
                print("Matched aliases :", skill["matched_aliases"])

                # Show the exact title/description location around
                # each matched alias when possible.
                for alias in skill["matched_aliases"]:
                    alias_lower = alias.lower()
                    text_lower = job_text.lower()
                    position = text_lower.find(alias_lower)

                    print()
                    print("Alias:", alias)

                    if position == -1:
                        print("  Found in job text: NO")
                        continue

                    print("  Found in job text: YES")
                    window_start = max(0, position - 120)
                    window_end = min(
                        len(job_text),
                        position + len(alias) + 120,
                    )

                    context = (
                        job_text[
                            window_start:window_end
                        ]
                        .replace("\n", " ")
                    )

                    print("  Context:")
                    print("  " + context)

        print_section("SUMMARY")

        print(
            "Suspicious mappings inspected:",
            suspicious_found,
        )

        if suspicious_found == 0:
            print(
                "No suspicious skill names from the "
                "inspection list were found."
            )

        print()
        print(
            "This script is read-only. It does not modify "
            "jobs, skills, skill_aliases, or job_skills."
        )

        print_section("INSPECTION COMPLETED")

    except Exception as error:
        connection.rollback()
        print_section("INSPECTION FAILED")
        print("Error type:", type(error).__name__)
        print("Error:", error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    inspect()
