import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.database import get_connection


RECENT_DAYS = 90
HALF_LIFE_DAYS = 30


def create_table(cursor):
    """
    Create the market statistics table if it does not exist.
    """

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_market_stats (
            skill_id INT PRIMARY KEY,

            job_count INT NOT NULL DEFAULT 0,

            recent_job_count INT NOT NULL DEFAULT 0,

            recency_weighted_count
                DECIMAL(12,4) NOT NULL DEFAULT 0,

            frequency_score
                DECIMAL(8,6) NOT NULL DEFAULT 0,

            recency_score
                DECIMAL(8,6) NOT NULL DEFAULT 0,

            market_score
                DECIMAL(8,6) NOT NULL DEFAULT 0,

            reference_date DATE NOT NULL,

            calculated_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,

            FOREIGN KEY (skill_id)
                REFERENCES skills(id)
                ON DELETE CASCADE
        )
        """
    )


def get_job_skill_rows(cursor):
    """
    Get all Role Radar job-skill mappings.
    """

    cursor.execute(
        """
        SELECT
            js.job_id,
            js.skill_id,
            j.posted_date
        FROM job_skills js
        JOIN jobs j
            ON j.id = js.job_id
        WHERE j.source = 'role-radar'
        """
    )

    return cursor.fetchall()


def calculate_decay(age_days):
    """
    Exponential recency decay.

    Every HALF_LIFE_DAYS, the weight becomes half.
    """

    if age_days < 0:
        age_days = 0

    return 0.5 ** (
        age_days / HALF_LIFE_DAYS
    )


def normalize_values(values):
    """
    Normalize positive values to [0, 1]
    using the maximum value.
    """

    if not values:
        return {}

    maximum = max(values.values())

    if maximum <= 0:
        return {
            key: 0.0
            for key in values
        }

    return {
        key: value / maximum
        for key, value in values.items()
    }


def build_statistics(rows):
    """
    Build frequency and recency demand statistics.
    """

    if not rows:
        return {}, None

    # Use only valid posting dates for temporal analysis.
    valid_dates = [
        row["posted_date"]
        for row in rows
        if row["posted_date"] is not None
    ]

    if valid_dates:
        reference_date = max(valid_dates)
    else:
        reference_date = date.today()

    skill_jobs = defaultdict(set)
    recent_skill_jobs = defaultdict(set)
    recency_weighted = defaultdict(float)

    for row in rows:

        skill_id = row["skill_id"]
        job_id = row["job_id"]
        posted_date = row["posted_date"]

        # Count every distinct job containing the skill.
        skill_jobs[skill_id].add(job_id)

        if posted_date is None:
            continue

        age_days = (
            reference_date - posted_date
        ).days

        if age_days < 0:
            # Should not normally happen because reference_date
            # is the latest date in the dataset.
            age_days = 0

        if age_days <= RECENT_DAYS:
            recent_skill_jobs[
                skill_id
            ].add(job_id)

        recency_weighted[
            skill_id
        ] += calculate_decay(age_days)

    job_counts = {
        skill_id: len(job_ids)
        for skill_id, job_ids
        in skill_jobs.items()
    }

    recent_counts = {
        skill_id: len(job_ids)
        for skill_id, job_ids
        in recent_skill_jobs.items()
    }

    # Log scaling prevents extremely frequent skills
    # from dominating the score.
    log_frequency = {
        skill_id: math.log1p(count)
        for skill_id, count
        in job_counts.items()
    }

    log_recency = {
        skill_id: math.log1p(
            recency_weighted.get(
                skill_id,
                0.0
            )
        )
        for skill_id in job_counts
    }

    frequency_scores = normalize_values(
        log_frequency
    )

    recency_scores = normalize_values(
        log_recency
    )

    statistics = {}

    for skill_id, job_count in job_counts.items():

        frequency_score = frequency_scores.get(
            skill_id,
            0.0
        )

        recency_score = recency_scores.get(
            skill_id,
            0.0
        )

        market_score = (
            0.6 * frequency_score
            + 0.4 * recency_score
        )

        statistics[skill_id] = {
            "job_count": job_count,
            "recent_job_count": recent_counts.get(
                skill_id,
                0
            ),
            "recency_weighted_count":
                recency_weighted.get(
                    skill_id,
                    0.0
                ),
            "frequency_score":
                frequency_score,
            "recency_score":
                recency_score,
            "market_score":
                market_score,
        }

    return statistics, reference_date


def save_statistics(cursor, statistics, reference_date):
    """
    Replace the existing Role Radar market statistics.
    """

    cursor.execute(
        """
        DELETE FROM skill_market_stats
        """
    )

    for skill_id, stats in statistics.items():

        cursor.execute(
            """
            INSERT INTO skill_market_stats
            (
                skill_id,
                job_count,
                recent_job_count,
                recency_weighted_count,
                frequency_score,
                recency_score,
                market_score,
                reference_date
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                skill_id,
                stats["job_count"],
                stats["recent_job_count"],
                stats["recency_weighted_count"],
                stats["frequency_score"],
                stats["recency_score"],
                stats["market_score"],
                reference_date,
            )
        )


def main():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        create_table(cursor)

        rows = get_job_skill_rows(
            cursor
        )

        print(
            f"Job-skill rows found: {len(rows)}"
        )

        if not rows:
            print(
                "No Role Radar job-skill data found."
            )
            return

        statistics, reference_date = (
            build_statistics(rows)
        )

        save_statistics(
            cursor,
            statistics,
            reference_date,
        )

        connection.commit()

        print()
        print(
            "Market statistics created."
        )
        print(
            f"Skills analyzed: "
            f"{len(statistics)}"
        )
        print(
            f"Reference date: "
            f"{reference_date}"
        )
        print(
            f"Recent window: "
            f"{RECENT_DAYS} days"
        )
        print(
            f"Recency half-life: "
            f"{HALF_LIFE_DAYS} days"
        )

    except Exception as error:
        connection.rollback()

        print(
            "Market statistics build failed."
        )
        print(error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()