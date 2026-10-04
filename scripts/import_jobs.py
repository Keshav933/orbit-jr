import json
import os
from datetime import datetime
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


DATA_FILE = Path(
    "data/processed/role-radar/jobs_final.json"
)


load_dotenv("backend/.env")


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


def get_date(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date()
    except ValueError:
        return None


def get_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).replace(tzinfo=None)
    except ValueError:
        return None


with open(
    DATA_FILE,
    "r",
    encoding="utf-8"
) as file:
    jobs = json.load(file)


connection = get_connection()
cursor = connection.cursor()


query = """
    INSERT INTO jobs (
        source,
        external_id,
        title,
        company_name,
        location,
        description,
        experience_min,
        is_remote,
        posted_date,
        source_url,
        seniority_level,
        employment_type,
        job_function,
        industry,
        role_family_hint,
        domain_hint,
        scraped_at
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON DUPLICATE KEY UPDATE
        title = VALUES(title),
        company_name = VALUES(company_name),
        location = VALUES(location),
        description = VALUES(description),
        experience_min = VALUES(experience_min),
        is_remote = VALUES(is_remote),
        posted_date = VALUES(posted_date),
        source_url = VALUES(source_url),
        seniority_level = VALUES(seniority_level),
        employment_type = VALUES(employment_type),
        job_function = VALUES(job_function),
        industry = VALUES(industry),
        role_family_hint = VALUES(role_family_hint),
        domain_hint = VALUES(domain_hint),
        scraped_at = VALUES(scraped_at)
"""


inserted = 0


for job in jobs:
    experience = job.get(
        "experience_years_hint"
    )

    if experience is not None:
        try:
            experience = float(experience)
        except (TypeError, ValueError):
            experience = None


    values = (
        "role-radar",
        job.get("id"),
        job.get("title"),
        job.get("company"),
        job.get("location"),
        job.get("description"),
        experience,
        bool(job.get("remote_hint", False)),
        get_date(job.get("posted_at")),
        job.get("url"),
        job.get("seniority_level"),
        job.get("employment_type"),
        job.get("job_function"),
        job.get("industry"),
        job.get("role_family_hint"),
        job.get("domain_hint"),
        get_datetime(job.get("scraped_at")),
    )


    cursor.execute(query, values)
    inserted += 1


connection.commit()

cursor.close()
connection.close()


print()
print("Job import completed.")
print("Jobs processed:", inserted)