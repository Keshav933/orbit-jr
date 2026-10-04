"""
ORBIT-JR - Test live job synchronization.

This script:
1. Reads one profile from MySQL.
2. Fetches jobs from the free live sources.
3. Inserts new jobs.
4. Updates jobs already known to ORBIT-JR.
5. Prints duplicate behavior.

Run from the project root:

    python scripts/test_live_job_sync.py 3

Replace 3 with your actual profile ID.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)


from backend.app.live_job_sync import (  # noqa: E402
    sync_profile_jobs,
)


def main() -> None:

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python scripts/test_live_job_sync.py <profile_id>"
        )

        sys.exit(1)

    try:

        profile_id = int(
            sys.argv[1]
        )

    except ValueError:

        print(
            "ERROR: profile_id must be an integer."
        )

        sys.exit(1)

    print(
        "ORBIT-JR LIVE JOB SYNCHRONIZATION TEST"
    )

    print(
        f"Profile ID: {profile_id}"
    )

    print()

    try:

        result = sync_profile_jobs(
            profile_id
        )

    except Exception as exc:

        print(
            "SYNC FAILED"
        )

        print(
            f"Error type: {type(exc).__name__}"
        )

        print(
            f"Error: {exc}"
        )

        raise

    print(
        "SYNC SUCCESS"
    )

    print()
    print(
        f"Jobs discovered       : "
        f"{result['discovered']}"
    )

    print(
        f"New jobs inserted     : "
        f"{result['inserted']}"
    )

    print(
        f"Existing jobs updated : "
        f"{result['updated_existing']}"
    )

    print(
        f"Skipped records       : "
        f"{result['skipped']}"
    )

    print(
        f"Unique DB job IDs     : "
        f"{result['unique_job_ids_in_sync']}"
    )

    if result["source_errors"]:

        print()
        print(
            "Source errors:"
        )

        for error in result[
            "source_errors"
        ]:

            print(
                f"- {error}"
            )

    print()

    print(
        "Job IDs synchronized:"
    )

    print(
        result["job_ids"]
    )


if __name__ == "__main__":
    main()
