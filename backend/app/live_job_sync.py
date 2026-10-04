"""

ORBIT-JR Live Job Synchronization Service



Purpose:

    Take jobs discovered by the free public-source layer,

    store them in MySQL, update existing jobs, and prevent

    duplicate live listings across repeated searches and

    supported sources.



This module does NOT:

    - call OpenAI

    - call Gemini

    - calculate recommendation scores

    - replace the existing ranking pipeline



It prepares the job corpus for the existing ORBIT-JR pipeline.

"""



from __future__ import annotations



import hashlib

from datetime import datetime

from typing import Any



from backend.app.database import get_connection

from backend.app.skill_extractor import extract_skills_from_text
from scripts.build_live_job_index import build_live_index
from scripts.extract_job_skills import (
    calculate_importance,
    classify_requirement,
)

from backend.app.live_job_research import (

    LiveJob,

    discover_live_jobs,

    get_profile_context,

)





# ---------------------------------------------------------

# Text normalization

# ---------------------------------------------------------



def normalize_key_text(value: Any) -> str:

    """

    Normalize company/title/location text for

    duplicate comparison.

    """



    text = str(

        value or ""

    ).strip().lower()



    replacements = {

        "bangalore": "bengaluru",

        "gurgaon": "gurugram",

        "remote / worldwide": "remote",

        "remote worldwide": "remote",

        "worldwide": "remote",

        "work from home": "remote",

    }



    for old, new in replacements.items():

        text = text.replace(

            old,

            new,

        )



    cleaned = []



    for character in text:

        if (

            character.isalnum()

            or character in {

                "+",

                "#",

                ".",

                " ",

            }

        ):

            cleaned.append(character)

        else:

            cleaned.append(" ")



    text = "".join(cleaned)



    return " ".join(

        text.split()

    )





def normalize_url(

    value: Any,

) -> str:



    text = str(

        value or ""

    ).strip()



    if not text:

        return ""



    text = text.lower()



    # Remove common tracking query strings.

    for marker in (

        "?utm_",

        "&utm_",

        "?gclid",

        "&gclid",

        "?fbclid",

        "&fbclid",

    ):



        position = text.find(

            marker

        )



        if position >= 0:

            text = text[

                :position

            ]



    return text.rstrip(

        "/"

    )





# ---------------------------------------------------------

# Cross-source duplicate key

# ---------------------------------------------------------



def build_canonical_key(

    job: LiveJob,

) -> str:

    """

    Build a stable key for the same opening appearing

    repeatedly or on more than one public source.



    Company + title + location is intentionally used

    for cross-source matching.



    Source URL is handled separately for exact-source

    matching.

    """



    company = normalize_key_text(

        job.company_name

    )



    title = normalize_key_text(

        job.title

    )



    location = normalize_key_text(

        job.location

    )



    raw_key = (

        f"{company}|"

        f"{title}|"

        f"{location}"

    )



    return hashlib.sha256(

        raw_key.encode(

            "utf-8"

        )

    ).hexdigest()





def has_enough_identity(

    job: LiveJob,

) -> bool:



    return bool(

        normalize_key_text(

            job.company_name

        )

        and normalize_key_text(

            job.title

        )

    )





# ---------------------------------------------------------

# Find existing job

# ---------------------------------------------------------



def find_existing_job(

    cursor,

    job: LiveJob,

    canonical_key: str,

) -> int | None:



    source_url = normalize_url(

        job.source_url

    )



    # -----------------------------------------------------

    # 1. Exact source URL match

    # -----------------------------------------------------

    # MySQL RTRIM() only accepts one argument.

    # TRIM(TRAILING '/' FROM value) is used instead

    # to ignore a trailing slash.

    # -----------------------------------------------------



    if source_url:



        cursor.execute(

            """

            SELECT id

            FROM jobs

            WHERE TRIM(

                TRAILING '/' FROM

                LOWER(source_url)

            ) = %s

            LIMIT 1

            """,

            (

                source_url,

            ),

        )



        row = cursor.fetchone()



        if row:

            return int(

                row[0]

            )



    # -----------------------------------------------------

    # 2. Cross-source canonical match

    # -----------------------------------------------------



    cursor.execute(

        """

        SELECT id

        FROM jobs

        WHERE canonical_key = %s

        LIMIT 1

        """,

        (

            canonical_key,

        ),

    )



    row = cursor.fetchone()



    if row:

        return int(

            row[0]

        )



    return None



# ---------------------------------------------------------

# Insert new live job

# ---------------------------------------------------------



def insert_job(

    cursor,

    job: LiveJob,

    canonical_key: str,

    now: datetime,

) -> int:



    posted_date = (

        job.posted_date

        or None

    )



    cursor.execute(

        """

        INSERT INTO jobs (

            source,

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

            seniority_level,

            employment_type,

            job_function,

            industry,

            scraped_at,

            source_type,

            application_url,

            canonical_key,

            is_active,

            first_seen_at,

            last_seen_at,

            last_verified_at,

            verification_status

        )

        VALUES (

            %s, %s, %s, %s, %s,

            %s, %s, %s, %s, %s,

            %s, %s, %s, %s, %s,

            %s, %s, %s, %s, %s,

            %s, %s, %s, %s

        )

        """,

        (

            job.source_name,

            job.external_id or None,

            job.title,

            job.company_name,

            job.location,

            job.description,

            job.experience_min,

            job.experience_max,

            int(job.is_remote),

            posted_date,

            job.source_url,

            job.seniority_level or None,

            job.employment_type or None,

            job.job_function or None,

            job.industry or None,

            now,

            job.source_type or None,

            job.application_url or None,

            canonical_key,

            1,

            now,

            now,

            now,

            "source_verified",

        ),

    )



    return int(

        cursor.lastrowid

    )





# ---------------------------------------------------------

# Update existing live job

# ---------------------------------------------------------



def update_job(

    cursor,

    job_id: int,

    job: LiveJob,

    canonical_key: str,

    now: datetime,

) -> None:



    posted_date = (

        job.posted_date

        or None

    )



    cursor.execute(

        """

        UPDATE jobs

        SET

            source = %s,

            external_id = %s,

            title = %s,

            company_name = %s,

            location = %s,

            description = %s,

            experience_min = %s,

            experience_max = %s,

            is_remote = %s,

            posted_date = %s,

            source_url = %s,

            seniority_level = %s,

            employment_type = %s,

            job_function = %s,

            industry = %s,

            scraped_at = %s,

            source_type = %s,

            application_url = %s,

            canonical_key = %s,

            is_active = 1,

            last_seen_at = %s,

            last_verified_at = %s,

            verification_status = %s

        WHERE id = %s

        """,

        (

            job.source_name,

            job.external_id or None,

            job.title,

            job.company_name,

            job.location,

            job.description,

            job.experience_min,

            job.experience_max,

            int(job.is_remote),

            posted_date,

            job.source_url,

            job.seniority_level or None,

            job.employment_type or None,

            job.job_function or None,

            job.industry or None,

            now,

            job.source_type or None,

            job.application_url or None,

            canonical_key,

            now,

            now,

            "source_verified",

            job_id,

        ),

    )





# ---------------------------------------------------------

# Sync discovered jobs

# ---------------------------------------------------------



def sync_job_skills(job_ids: list[int]) -> dict[str, Any]:
    """
    Rebuild skill mappings only for the jobs synchronized
    during the current live-job refresh.
    """

    unique_job_ids = sorted(
        set(int(job_id) for job_id in job_ids)
    )

    if not unique_job_ids:
        return {
            "processed_jobs": 0,
            "jobs_with_detected_skills": 0,
            "jobs_without_detected_skills": 0,
            "total_job_skill_mappings": 0,
        }

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    placeholders = ", ".join(
        ["%s"] * len(unique_job_ids)
    )

    try:
        cursor.execute(
            f"""
            SELECT
                id,
                title,
                description,
                source_type
            FROM jobs
            WHERE id IN ({placeholders})
              AND source_type IN (
                  'jobicy',
                  'himalayas',
                  'remoteok'
              )
            ORDER BY id
            """,
            tuple(unique_job_ids),
        )

        jobs = cursor.fetchall()

        # Remove old mappings only for the jobs synchronized now.
        cursor.execute(
            f"""
            DELETE FROM job_skills
            WHERE job_id IN ({placeholders})
            """,
            tuple(unique_job_ids),
        )

        jobs_with_skills = 0
        total_mappings = 0

        for job in jobs:
            title = job["title"] or ""
            description = job["description"] or ""
            job_text = f"{title}\n{description}"

            detected_skills = extract_skills_from_text(
                job_text
            )

            if detected_skills:
                jobs_with_skills += 1

            for skill in detected_skills:
                importance = calculate_importance(
                    title,
                    skill,
                )

                requirement_type = classify_requirement(
                    job_text,
                    skill["matched_aliases"],
                )

                cursor.execute(
                    """
                    INSERT INTO job_skills
                    (
                        job_id,
                        skill_id,
                        importance,
                        requirement_type
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        job["id"],
                        skill["skill_id"],
                        importance,
                        requirement_type,
                    ),
                )

                total_mappings += 1

        connection.commit()

        return {
            "processed_jobs": len(jobs),
            "jobs_with_detected_skills": jobs_with_skills,
            "jobs_without_detected_skills": (
                len(jobs) - jobs_with_skills
            ),
            "total_job_skill_mappings": total_mappings,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def sync_profile_jobs(

    profile_id: int,

) -> dict[str, Any]:



    profile = get_profile_context(

        profile_id

    )



    discovered_jobs, errors = (

        discover_live_jobs(

            profile

        )

    )



    connection = get_connection()

    cursor = connection.cursor()



    inserted = 0

    updated = 0

    skipped = 0

    job_ids: list[int] = []



    now = datetime.now()



    try:



        for job in discovered_jobs:



            # -------------------------------------------------

            # Ignore incomplete records.

            # -------------------------------------------------



            if not has_enough_identity(

                job

            ):



                skipped += 1

                continue



            if not normalize_url(

                job.source_url

            ):



                skipped += 1

                continue



            canonical_key = (

                build_canonical_key(

                    job

                )

            )



            existing_id = (

                find_existing_job(

                    cursor,

                    job,

                    canonical_key,

                )

            )



            if existing_id is None:



                job_id = insert_job(

                    cursor,

                    job,

                    canonical_key,

                    now,

                )



                inserted += 1



            else:



                job_id = existing_id



                update_job(

                    cursor,

                    job_id,

                    job,

                    canonical_key,

                    now,

                )



                updated += 1



            job_ids.append(

                job_id

            )



        connection.commit()



    except Exception:



        connection.rollback()

        raise



    finally:



        cursor.close()

        connection.close()



    unique_job_ids = sorted(set(job_ids))
    skill_extraction = sync_job_skills(
        unique_job_ids
    )

    live_index = build_live_index()

    return {

        "status": "success",

        "profile_id": profile_id,

        "discovered": len(

            discovered_jobs

        ),

        "inserted": inserted,

        "updated_existing": updated,

        "skipped": skipped,

        "unique_job_ids_in_sync": len(unique_job_ids),

        "job_ids": unique_job_ids,

        "skill_extraction": skill_extraction,

        "live_index": live_index,

        "source_errors": errors,

    }
