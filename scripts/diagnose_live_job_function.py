from pathlib import Path
import sys
from collections import Counter


# -------------------------------------------------------------------
# Add project root to Python path.
# This allows the script to import the backend package correctly.
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.database import get_connection
from backend.app.live_job_sync import get_profile_context
from backend.app.live_job_research import discover_live_jobs


PROFILE_ID = 1
MAX_JOB_FUNCTION_LENGTH = 255


def check_database(cursor):
    print("\n" + "=" * 80)
    print("DATABASE CHECK")
    print("=" * 80)

    cursor.execute("SELECT DATABASE()")
    database_name = cursor.fetchone()[0]

    print("Database:", database_name)

    cursor.execute(
        """
        SELECT
            COLUMN_NAME,
            COLUMN_TYPE,
            CHARACTER_MAXIMUM_LENGTH
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'jobs'
          AND column_name = 'job_function'
        """
    )

    column = cursor.fetchone()

    if column:
        print("Column name:", column[0])
        print("Column type:", column[1])
        print("Maximum length:", column[2])
    else:
        print("job_function column was not found.")

    cursor.execute(
        """
        SELECT MAX(CHAR_LENGTH(job_function))
        FROM jobs
        """
    )

    longest_value = cursor.fetchone()[0]

    print("Longest existing job_function:", longest_value)


def check_live_jobs():
    print("\n" + "=" * 80)
    print("LIVE JOB SOURCE CHECK")
    print("=" * 80)

    print("Profile ID:", PROFILE_ID)

    profile = get_profile_context(PROFILE_ID)

    if profile is None:
        print("ERROR: Profile not found.")
        return

    jobs, errors = discover_live_jobs(profile)

    print("Jobs discovered:", len(jobs))
    print("Source errors:", errors)

    bad_jobs = [
        job
        for job in jobs
        if job.job_function
        and len(job.job_function) > MAX_JOB_FUNCTION_LENGTH
    ]

    print(
        "Jobs with job_function longer than",
        MAX_JOB_FUNCTION_LENGTH,
        ":",
        len(bad_jobs),
    )

    if not bad_jobs:
        print("\nNo oversized job_function values found.")
        return

    print("\n" + "-" * 80)
    print("OVERSIZED JOB_FUNCTION VALUES")
    print("-" * 80)

    for index, job in enumerate(bad_jobs, start=1):
        print(f"\n[{index}]")
        print("Source :", job.source_name)
        print("Title  :", job.title)
        print("Company:", job.company_name)
        print("Length :", len(job.job_function))
        print("Value  :", repr(job.job_function[:500]))

    source_counts = Counter(
        job.source_name
        for job in bad_jobs
    )

    print("\n" + "-" * 80)
    print("OVERSIZED VALUES BY SOURCE")
    print("-" * 80)

    for source, count in source_counts.items():
        print(f"{source}: {count}")


def main():
    print("ORBIT-JR LIVE JOB FUNCTION DIAGNOSTIC")
    print("=" * 80)

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        check_database(cursor)
        check_live_jobs()

        print("\n" + "=" * 80)
        print("DIAGNOSTIC COMPLETED")
        print("=" * 80)

    except Exception as error:
        print("\nDIAGNOSTIC FAILED")
        print("Error type:", type(error).__name__)
        print("Error:", error)

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


if __name__ == "__main__":
    main()