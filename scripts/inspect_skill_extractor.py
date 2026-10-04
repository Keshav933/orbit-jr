from pathlib import Path
import sys
import inspect
import importlib


# ---------------------------------------------------------
# Make imports work from scripts/
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def inspect_skill_extractor():
    print_section("SKILL EXTRACTOR MODULE")

    module = importlib.import_module(
        "backend.app.skill_extractor"
    )

    print("Module file:")
    print(module.__file__)

    print("\nPublic functions:")

    functions = []

    for name, value in inspect.getmembers(
        module,
        inspect.isfunction,
    ):
        if name.startswith("_"):
            continue

        functions.append(
            (
                name,
                value,
            )
        )

    if not functions:
        print("No public functions found.")
        return

    for name, function in functions:
        try:
            signature = inspect.signature(
                function
            )
        except Exception:
            signature = "(signature unavailable)"

        print(
            f"- {name}{signature}"
        )


def inspect_job_skill_schema():
    print_section("JOB_SKILLS DATABASE SCHEMA")

    from backend.app.database import get_connection

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                COLUMN_NAME,
                COLUMN_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'job_skills'
            ORDER BY ORDINAL_POSITION
            """
        )

        rows = cursor.fetchall()

        if not rows:
            print("job_skills table was not found.")
            return

        for row in rows:
            print(
                f"{row[0]:20} "
                f"{row[1]:20} "
                f"NULL={row[2]:3} "
                f"DEFAULT={row[3]}"
            )

    finally:
        cursor.close()
        connection.close()


def inspect_existing_skill_data():
    print_section("EXISTING SKILL DATA")

    from backend.app.database import get_connection

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM skills
            """
        )

        skill_count = cursor.fetchone()[0]

        print(
            "Total skills:",
            skill_count,
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM skill_aliases
            """
        )

        alias_count = cursor.fetchone()[0]

        print(
            "Total skill aliases:",
            alias_count,
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM job_skills
            """
        )

        job_skill_count = cursor.fetchone()[0]

        print(
            "Total job_skills mappings:",
            job_skill_count,
        )

    finally:
        cursor.close()
        connection.close()


def main():
    print("ORBIT-JR SKILL EXTRACTOR INSPECTION")
    print("=" * 80)

    try:
        inspect_skill_extractor()
        inspect_job_skill_schema()
        inspect_existing_skill_data()

        print_section("INSPECTION COMPLETED")

    except Exception as error:
        print("\nINSPECTION FAILED")
        print(
            "Error type:",
            type(error).__name__,
        )
        print(
            "Error:",
            error,
        )


if __name__ == "__main__":
    main()