import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.database import get_connection


connection = get_connection()
cursor = connection.cursor(dictionary=True)

try:
    cursor.execute(
        """
        SELECT
            s.name AS skill_name,
            ms.job_count,
            ms.recent_job_count,
            ms.frequency_score,
            ms.recency_score,
            ms.market_score,
            ms.reference_date
        FROM skill_market_stats ms
        JOIN skills s
            ON s.id = ms.skill_id
        ORDER BY ms.market_score DESC
        LIMIT 20
        """
    )

    rows = cursor.fetchall()

    print()
    print("Top market-demand skills")
    print("=" * 80)

    for index, row in enumerate(
        rows,
        start=1,
    ):
        print(
            f"{index}. "
            f"{row['skill_name']}"
        )

        print(
            f"   Jobs: "
            f"{row['job_count']}"
        )

        print(
            f"   Recent jobs: "
            f"{row['recent_job_count']}"
        )

        print(
            f"   Frequency score: "
            f"{float(row['frequency_score']):.4f}"
        )

        print(
            f"   Recency score: "
            f"{float(row['recency_score']):.4f}"
        )

        print(
            f"   Market score: "
            f"{float(row['market_score']):.4f}"
        )

        print(
            f"   Reference date: "
            f"{row['reference_date']}"
        )

        print()

finally:
    cursor.close()
    connection.close()