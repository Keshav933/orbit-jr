"""
Test ORBIT-JR free live job sources without touching MySQL.

Run from the project root:
    python scripts/test_live_job_sources.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.live_job_research import (  # noqa: E402
    ProfileContext,
    fetch_himalayas,
    fetch_jobicy,
    fetch_remote_ok,
    load_sources,
)


def run_source(name, function, profile):
    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    try:
        jobs = function(profile)

        print(f"Status : SUCCESS")
        print(f"Jobs   : {len(jobs)}")

        for index, job in enumerate(jobs[:3], start=1):
            print()
            print(f"{index}. {job.title}")
            print(f"   Company : {job.company_name}")
            print(f"   Location: {job.location}")
            print(f"   Source  : {job.source_name}")
            print(f"   URL     : {job.source_url}")

    except Exception as exc:
        print("Status : FAILED")
        print(f"Type   : {type(exc).__name__}")
        print(f"Error  : {exc}")


def main():
    print("ORBIT-JR FREE LIVE JOB SOURCE TEST")
    print(f"Project: {PROJECT_ROOT}")

    profile = ProfileContext(
        profile_id=0,
        education="B.Tech Computer Science",
        experience_years=0,
        location="India",
        preferred_role="Software Developer",
        summary="B.Tech CSE student seeking entry-level software jobs.",
        skills=[
            "Python",
            "JavaScript",
            "React",
            "SQL",
            "MySQL",
        ],
    )

    sources = load_sources()

    print()
    print(f"Configured ATS sources: {len(sources)}")

    for source in sources:
        print(
            f"- {source.get('type')}: "
            f"{source.get('company')} "
            f"(enabled={source.get('enabled', True)})"
        )

    run_source(
        "JOBICY",
        fetch_jobicy,
        profile,
    )

    run_source(
        "HIMALAYAS",
        fetch_himalayas,
        profile,
    )

    run_source(
        "REMOTE OK",
        fetch_remote_ok,
        profile,
    )


if __name__ == "__main__":
    main()
