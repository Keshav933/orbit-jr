import html
import re

from backend.app.database import get_connection


def clean_description(text):
    """
    Convert basic HTML content into readable text.
    """

    if not text:
        return ""

    text = html.unescape(str(text))

    # Convert common HTML block tags into spaces.
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</p>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    # Remove remaining HTML tags.
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # Clean whitespace.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def get_job_details(job_id):
    """
    Get complete information about one job.
    """

    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    try:
        cursor.execute(
            """
            SELECT
                id,
                source,
                source_type,
                external_id,
                title,
                company_name,
                location,
                description,
                experience_min,
                experience_max,
                is_remote,
                posted_date,
                source_url,
                application_url,
                seniority_level,
                employment_type,
                job_function,
                industry,
                role_family_hint,
                domain_hint
            FROM jobs
            WHERE id = %s
            """,
            (job_id,),
        )

        job = cursor.fetchone()

        if not job:
            return None

        job["description"] = clean_description(
            job["description"]
        )

        cursor.execute(
            """
            SELECT
                js.skill_id,
                s.name AS skill_name,
                js.importance,
                js.requirement_type
            FROM job_skills js
            JOIN skills s
                ON s.id = js.skill_id
            WHERE js.job_id = %s
            ORDER BY
                js.requirement_type,
                js.importance DESC,
                s.name
            """,
            (job_id,),
        )

        skills = cursor.fetchall()

        job["skills"] = skills

        return job

    finally:
        cursor.close()
        connection.close()
