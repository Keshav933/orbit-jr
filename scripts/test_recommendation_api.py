import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Add project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import get_connection


API_BASE_URL = "http://127.0.0.1:8000"
PROFILE_ID = 1

LIVE_SOURCE_TYPES = {
    "jobicy",
    "himalayas",
    "remoteok",
}

REQUIRED_RESPONSE_KEYS = {
    "profile_id",
    "count",
    "recommendations",
}


def print_section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def fetch_recommendations(profile_id):
    url = (
        f"{API_BASE_URL}/api/v1/recommendations/"
        f"{profile_id}"
    )

    request = Request(
        url,
        headers={
            "Accept": "application/json",
        },
        method="GET",
    )

    with urlopen(
        request,
        timeout=60,
    ) as response:

        status_code = response.status
        body = response.read().decode(
            "utf-8"
        )

    data = json.loads(body)

    return status_code, data


def get_source_map(job_ids):
    if not job_ids:
        return {}

    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    placeholders = ", ".join(
        ["%s"] * len(job_ids)
    )

    try:
        cursor.execute(
            f"""
            SELECT
                id,
                source,
                source_type
            FROM jobs
            WHERE id IN ({placeholders})
            """,
            tuple(job_ids),
        )

        rows = cursor.fetchall()

        return {
            row["id"]: (
                "LIVE"
                if row["source_type"] in LIVE_SOURCE_TYPES
                else "ROLE-RADAR"
            )
            for row in rows
        }

    finally:
        cursor.close()
        connection.close()


def main():
    profile_id = PROFILE_ID

    if len(sys.argv) > 1:
        try:
            profile_id = int(sys.argv[1])
        except ValueError:
            print(
                "Invalid profile ID:",
                sys.argv[1],
            )
            return

    print("ORBIT-JR RECOMMENDATION API TEST")
    print("=" * 100)
    print("API:", API_BASE_URL)
    print("Profile ID:", profile_id)

    try:
        status_code, data = fetch_recommendations(
            profile_id
        )

        print_section("HTTP RESPONSE")

        print("Status code:", status_code)

        if status_code != 200:
            print(
                "FAIL: Recommendation endpoint "
                "did not return HTTP 200."
            )
            print("Response:")
            print(data)
            return

        print(
            "PASS: Recommendation endpoint "
            "returned HTTP 200."
        )

        if not isinstance(data, dict):
            print(
                "FAIL: Response body is not a JSON object."
            )
            return

        print_section("RESPONSE STRUCTURE")

        missing_keys = (
            REQUIRED_RESPONSE_KEYS - set(data.keys())
        )

        if missing_keys:
            print(
                "FAIL: Missing response keys:",
                sorted(missing_keys),
            )
            print(
                "Available keys:",
                sorted(data.keys()),
            )
            return

        print(
            "PASS: Required response keys are present."
        )

        print("profile_id:", data["profile_id"])
        print("count:", data["count"])

        recommendations = data[
            "recommendations"
        ]

        if not isinstance(
            recommendations,
            list,
        ):
            print(
                "FAIL: 'recommendations' "
                "is not a list."
            )
            return

        print(
            "Actual recommendation records:",
            len(recommendations),
        )

        if data["profile_id"] != profile_id:
            print(
                "WARNING: Response profile_id does not "
                "match requested profile."
            )

        if data["count"] != len(
            recommendations
        ):
            print(
                "WARNING: Response count does not "
                "match recommendation list length."
            )
        else:
            print(
                "PASS: count matches recommendation list length."
            )

        if not recommendations:
            print(
                "No recommendations were returned."
            )
            return

        job_ids = [
            recommendation.get("job_id")
            for recommendation in recommendations
            if recommendation.get("job_id") is not None
        ]

        source_map = get_source_map(
            job_ids
        )

        live_results = [
            recommendation
            for recommendation in recommendations
            if source_map.get(
                recommendation.get("job_id")
            ) == "LIVE"
        ]

        role_radar_results = [
            recommendation
            for recommendation in recommendations
            if source_map.get(
                recommendation.get("job_id")
            ) == "ROLE-RADAR"
        ]

        print_section(
            "RECOMMENDATION SOURCE CHECK"
        )

        print(
            "Role Radar recommendations:",
            len(role_radar_results),
        )

        print(
            "Live recommendations:",
            len(live_results),
        )

        print_section(
            "RECOMMENDATIONS"
        )

        header = (
            f"{'RANK':<6}"
            f"{'JOB ID':<9}"
            f"{'SOURCE':<12}"
            f"{'FINAL':<10}"
            f"{'CONF':<10}"
            f"{'SKILLS':<9}"
            "TITLE"
        )

        print(header)
        print("-" * 100)

        for rank, recommendation in enumerate(
            recommendations,
            start=1,
        ):
            job_id = recommendation.get(
                "job_id"
            )

            source = source_map.get(
                job_id,
                "UNKNOWN",
            )

            print(
                f"{rank:<6}"
                f"{str(job_id):<9}"
                f"{source:<12}"
                f"{str(recommendation.get('final_score', 'N/A')):<10}"
                f"{str(recommendation.get('confidence', 'N/A')):<10}"
                f"{str(recommendation.get('matched_skill_count', 'N/A')):<9}"
                f"{recommendation.get('title', 'N/A')}"
            )

        print_section(
            "LIVE RECOMMENDATION DETAILS"
        )

        if not live_results:
            print(
                "No live jobs are present in the "
                "current API recommendation response."
            )
        else:
            for recommendation in live_results:
                print()
                print(
                    "Job ID:",
                    recommendation.get("job_id"),
                )
                print(
                    "Title:",
                    recommendation.get("title"),
                )
                print(
                    "Company:",
                    recommendation.get("company_name"),
                )
                print(
                    "Location:",
                    recommendation.get("location"),
                )
                print(
                    "Final score:",
                    recommendation.get("final_score"),
                )
                print(
                    "Confidence:",
                    recommendation.get("confidence"),
                )
                print(
                    "Source URL:",
                    recommendation.get("source_url"),
                )
                print(
                    "Matched skills:",
                    recommendation.get(
                        "matched_skills",
                        [],
                    ),
                )
                print(
                    "Required gaps:",
                    recommendation.get(
                        "required_gaps",
                        [],
                    ),
                )
                print(
                    "Preferred gaps:",
                    recommendation.get(
                        "preferred_gaps",
                        [],
                    ),
                )
                print(
                    "Evidence count:",
                    len(
                        recommendation.get(
                            "evidence",
                            [],
                        )
                    ),
                )

        print_section("FIELD VALIDATION")

        failures = []

        for index, recommendation in enumerate(
            recommendations,
            start=1,
        ):
            required_fields = (
                "job_id",
                "title",
                "company_name",
                "location",
                "source_url",
                "final_score",
                "confidence",
                "matched_skills",
            )

            missing = [
                field
                for field in required_fields
                if field not in recommendation
            ]

            if missing:
                failures.append(
                    (
                        index,
                        recommendation.get(
                            "job_id"
                        ),
                        missing,
                    )
                )

        if failures:
            print(
                "FAIL: Some recommendations "
                "are missing expected fields."
            )

            for rank, job_id, missing in failures:
                print(
                    f"  Rank {rank}, Job {job_id}: "
                    f"missing {missing}"
                )
        else:
            print(
                "PASS: All recommendations contain "
                "the expected core fields."
            )

        if live_results:
            print(
                "PASS: The API is returning at least "
                "one live-job recommendation."
            )
        else:
            print(
                "CHECK NEEDED: The API response contains "
                "no live-job recommendation in its "
                "current top results."
            )

        print_section(
            "RECOMMENDATION API TEST COMPLETED"
        )

    except HTTPError as error:
        print_section("API TEST FAILED")
        print("HTTP status:", error.code)

        try:
            body = error.read().decode("utf-8")
            print("Response:", body)
        except Exception:
            print("Could not read error response.")

    except URLError as error:
        print_section("API TEST FAILED")
        print(
            "Could not connect to FastAPI."
        )
        print(
            "Make sure the backend is running at:",
            API_BASE_URL,
        )
        print("Error:", error)

    except Exception as error:
        print_section("API TEST FAILED")
        print("Error type:", type(error).__name__)
        print("Error:", error)


if __name__ == "__main__":
    main()
