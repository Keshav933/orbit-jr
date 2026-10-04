from pathlib import Path
import sys


# ---------------------------------------------------------
# Make backend imports work when this script is run
# from the project root.
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.database import get_connection


LIVE_SOURCE_TYPES = (
    "jobicy",
    "himalayas",
    "remoteok",
)


def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main():
    print("ORBIT-JR LIVE JOB SKILL DIAGNOSTIC")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # -------------------------------------------------
        # 1. Database
        # -------------------------------------------------

        print_section("DATABASE")

        cursor.execute("SELECT DATABASE()")
        print("Database:", cursor.fetchone()[0])

        # -------------------------------------------------
        # 2. Live jobs by source
        # -------------------------------------------------

        print_section("LIVE JOBS BY SOURCE")

        cursor.execute(
            """
            SELECT
                source_type,
                COUNT(*) AS job_count
            FROM jobs
            WHERE source_type IN ('jobicy', 'himalayas', 'remoteok')
            GROUP BY source_type
            ORDER BY source_type
            """
        )

        source_rows = cursor.fetchall()

        total_live_jobs = 0

        for row in source_rows:
            source_type = row[0]
            job_count = int(row[1])

            total_live_jobs += job_count

            print(
                f"{source_type:12} : {job_count}"
            )

        print(
            "TOTAL LIVE JOBS:",
            total_live_jobs,
        )

        # -------------------------------------------------
        # 3. Total job_skills mappings for live jobs
        # -------------------------------------------------

        print_section("JOB SKILL MAPPINGS")

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM job_skills js
            INNER JOIN jobs j
                ON j.id = js.job_id
            WHERE j.source_type IN (
                'jobicy',
                'himalayas',
                'remoteok'
            )
            """
        )

        total_mappings = cursor.fetchone()[0]

        print(
            "Total live job_skills mappings:",
            total_mappings,
        )

        # -------------------------------------------------
        # 4. Number of live jobs having at least one skill
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(DISTINCT j.id)
            FROM jobs j
            INNER JOIN job_skills js
                ON js.job_id = j.id
            WHERE j.source_type IN (
                'jobicy',
                'himalayas',
                'remoteok'
            )
            """
        )

        jobs_with_skills = cursor.fetchone()[0]

        print(
            "Live jobs with skills:",
            jobs_with_skills,
        )

        # -------------------------------------------------
        # 5. Number of live jobs with no skills
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM jobs j
            LEFT JOIN job_skills js
                ON js.job_id = j.id
            WHERE j.source_type IN (
                'jobicy',
                'himalayas',
                'remoteok'
            )
            AND js.id IS NULL
            """
        )

        jobs_without_skills = cursor.fetchone()[0]

        print(
            "Live jobs WITHOUT skills:",
            jobs_without_skills,
        )

        # -------------------------------------------------
        # 6. Average skills per live job
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                ROUND(
                    COUNT(js.id) /
                    NULLIF(COUNT(DISTINCT j.id), 0),
                    2
                )
            FROM jobs j
            LEFT JOIN job_skills js
                ON js.job_id = j.id
            WHERE j.source_type IN (
                'jobicy',
                'himalayas',
                'remoteok'
            )
            """
        )

        average_skills = cursor.fetchone()[0]

        print(
            "Average skills per live job:",
            average_skills,
        )

        # -------------------------------------------------
        # 7. Skill mappings by source
        # -------------------------------------------------

        print_section("SKILL MAPPINGS BY SOURCE")

        cursor.execute(
            """
            SELECT
                j.source_type,
                COUNT(js.id) AS mapping_count,
                COUNT(DISTINCT j.id) AS jobs_with_mapping
            FROM jobs j
            LEFT JOIN job_skills js
                ON js.job_id = j.id
            WHERE j.source_type IN (
                'jobicy',
                'himalayas',
                'remoteok'
            )
            GROUP BY j.source_type
            ORDER BY j.source_type
            """
        )

        mapping_rows = cursor.fetchall()

        for row in mapping_rows:
            print(
                f"{row[0]:12} : "
                f"{row[1]} mappings, "
                f"{row[2]} jobs with mappings"
            )

        # -------------------------------------------------
        # 8. Show live jobs without skills
        # -------------------------------------------------

        print_section("SAMPLE LIVE JOBS WITHOUT SKILLS")

        cursor.execute(
            """
            SELECT
                j.id,
                j.source_type,
                j.title,
                j.company_name
            FROM jobs j
            LEFT JOIN job_skills js
                ON js.job_id = j.id
            WHERE j.source_type IN (
                'jobicy',
                'himalayas',
                'remoteok'
            )
            AND js.id IS NULL
            ORDER BY j.id DESC
            LIMIT 20
            """
        )

        missing_rows = cursor.fetchall()

        if not missing_rows:
            print("None.")
        else:
            for row in missing_rows:
                print(
                    f"ID={row[0]} | "
                    f"Source={row[1]} | "
                    f"Title={row[2]} | "
                    f"Company={row[3]}"
                )

        # -------------------------------------------------
        # 9. Sample live jobs WITH skills
        # -------------------------------------------------

        print_section("SAMPLE LIVE JOBS WITH SKILLS")

        cursor.execute(
            """
            SELECT
                j.id,
                j.source_type,
                j.title,
                COUNT(js.id) AS skill_count
            FROM jobs j
            INNER JOIN job_skills js
                ON js.job_id = j.id
            WHERE j.source_type IN (
                'jobicy',
                'himalayas',
                'remoteok'
            )
            GROUP BY
                j.id,
                j.source_type,
                j.title
            ORDER BY j.id DESC
            LIMIT 10
            """
        )

        skill_rows = cursor.fetchall()

        if not skill_rows:
            print("No live jobs currently have job_skills.")
        else:
            for row in skill_rows:
                print(
                    f"ID={row[0]} | "
                    f"Source={row[1]} | "
                    f"Skills={row[3]} | "
                    f"Title={row[2]}"
                )

        print_section("DIAGNOSTIC COMPLETED")

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