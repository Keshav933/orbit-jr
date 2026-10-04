"""
ORBIT-JR - Live Job Storage Database Migration

Run from project root:

    python scripts/setup_live_job_storage.py

This script safely adds the columns and indexes needed
for live job ingestion and global duplicate protection.

It does NOT delete existing jobs.
It does NOT import any live jobs.
"""

from __future__ import annotations

import sys
from pathlib import Path


# ---------------------------------------------------------
# Project root
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)


from backend.app.database import get_connection  # noqa: E402


# ---------------------------------------------------------
# Column definitions
# ---------------------------------------------------------

COLUMNS = {
    (
        "jobs",
        "source_type",
    ): "VARCHAR(50) NULL",

    (
        "jobs",
        "application_url",
    ): "VARCHAR(1000) NULL",

    (
        "jobs",
        "canonical_key",
    ): "VARCHAR(64) NULL",

    (
        "jobs",
        "is_active",
    ): "TINYINT(1) NOT NULL DEFAULT 1",

    (
        "jobs",
        "first_seen_at",
    ): "DATETIME NULL",

    (
        "jobs",
        "last_seen_at",
    ): "DATETIME NULL",

    (
        "jobs",
        "last_verified_at",
    ): "DATETIME NULL",

    (
        "jobs",
        "verification_status",
    ): "VARCHAR(40) NULL",
}


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def column_exists(
    cursor,
    table_name: str,
    column_name: str,
) -> bool:

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (
            table_name,
            column_name,
        ),
    )

    result = cursor.fetchone()

    return bool(
        result
        and int(result[0]) > 0
    )


def index_exists(
    cursor,
    table_name: str,
    index_name: str,
) -> bool:

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (
            table_name,
            index_name,
        ),
    )

    result = cursor.fetchone()

    return bool(
        result
        and int(result[0]) > 0
    )


def add_index_if_missing(
    cursor,
    table_name: str,
    index_name: str,
    sql: str,
) -> None:

    if index_exists(
        cursor,
        table_name,
        index_name,
    ):

        print(
            f"Already exists: "
            f"{index_name}"
        )

        return

    cursor.execute(sql)

    print(
        f"Added index: "
        f"{index_name}"
    )


# ---------------------------------------------------------
# Migration
# ---------------------------------------------------------

def main() -> None:

    print(
        "ORBIT-JR LIVE JOB STORAGE MIGRATION"
    )

    print(
        f"Project: {PROJECT_ROOT}"
    )

    connection = get_connection()

    cursor = connection.cursor()

    try:

        print()
        print(
            "Checking jobs table..."
        )

        for (
            table_name,
            column_name,
        ), definition in COLUMNS.items():

            if column_exists(
                cursor,
                table_name,
                column_name,
            ):

                print(
                    f"Already exists: "
                    f"{table_name}.{column_name}"
                )

                continue

            cursor.execute(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name}
                {definition}
                """
            )

            print(
                f"Added: "
                f"{table_name}.{column_name}"
            )

        print()
        print(
            "Creating indexes..."
        )

        # Unique canonical key.
        # Existing rows can safely remain NULL.
        add_index_if_missing(
            cursor,
            "jobs",
            "uq_jobs_canonical_key",
            """
            ALTER TABLE jobs
            ADD UNIQUE INDEX
            uq_jobs_canonical_key
            (canonical_key)
            """,
        )

        # Source URL lookup.
        # A prefix is used because source_url is VARCHAR(1000).
        add_index_if_missing(
            cursor,
            "jobs",
            "idx_jobs_source_url",
            """
            ALTER TABLE jobs
            ADD INDEX
            idx_jobs_source_url
            (source_url(191))
            """,
        )

        # Active job filtering.
        add_index_if_missing(
            cursor,
            "jobs",
            "idx_jobs_is_active",
            """
            ALTER TABLE jobs
            ADD INDEX
            idx_jobs_is_active
            (is_active)
            """,
        )

        # Fast source/date refresh lookup.
        add_index_if_missing(
            cursor,
            "jobs",
            "idx_jobs_last_seen_at",
            """
            ALTER TABLE jobs
            ADD INDEX
            idx_jobs_last_seen_at
            (last_seen_at)
            """,
        )

        connection.commit()

        print()
        print(
            "Migration completed successfully."
        )

        print()
        print(
            "No existing job records were deleted."
        )

        print(
            "No live jobs were imported yet."
        )

    except Exception as exc:

        connection.rollback()

        print()
        print(
            "Migration FAILED."
        )

        print(
            f"Error type: {type(exc).__name__}"
        )

        print(
            f"Error: {exc}"
        )

        raise

    finally:

        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
