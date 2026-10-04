from collections import defaultdict

from backend.app.database import get_connection


def get_profile_skills(profile_id):
    """
    Get all skills belonging to a candidate profile.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                ps.skill_id,
                s.name AS skill_name
            FROM profile_skills ps
            JOIN skills s
                ON s.id = ps.skill_id
            WHERE ps.profile_id = %s
              AND ps.source = 'resume'
            ORDER BY s.name
            """,
            (profile_id,),
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def get_role_radar_jobs():
    """
    Get Role Radar jobs together with their extracted skills.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                j.id AS job_id,
                j.title,
                j.company_name,
                j.location,
                j.description,
                j.source_url,
                js.skill_id,
                js.importance,
                js.requirement_type,
                s.name AS skill_name
            FROM jobs j
            JOIN job_skills js
                ON js.job_id = j.id
            JOIN skills s
                ON s.id = js.skill_id
            WHERE j.source = 'role-radar'
            ORDER BY j.id
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def calculate_job_score(profile_skill_ids, job_skills):
    """
    Calculate weighted skill-overlap score.

    Required skill:
        full importance

    Preferred skill:
        half importance

    Returns:
        score, matched_skills
    """

    total_weight = 0.0
    matched_weight = 0.0

    matched_skills = []

    for skill in job_skills:

        importance = float(
            skill["importance"] or 1.0
        )

        if skill["requirement_type"] == "preferred":
            importance *= 0.5

        total_weight += importance

        if skill["skill_id"] in profile_skill_ids:

            matched_weight += importance

            matched_skills.append(
                {
                    "skill_id": skill["skill_id"],
                    "skill_name": skill["skill_name"],
                }
            )

    if total_weight == 0:
        return 0.0, []

    score = matched_weight / total_weight

    return score, matched_skills


def retrieve_jobs(profile_id, top_k=10):
    """
    Retrieve the top jobs for a candidate profile
    using weighted lexical skill overlap.
    """

    profile_skills = get_profile_skills(
        profile_id
    )

    if not profile_skills:
        return []

    profile_skill_ids = {
        skill["skill_id"]
        for skill in profile_skills
    }

    rows = get_role_radar_jobs()

    jobs = defaultdict(list)

    for row in rows:
        jobs[row["job_id"]].append(row)

    results = []

    for job_id, job_skills in jobs.items():

        first_row = job_skills[0]

        score, matched_skills = calculate_job_score(
            profile_skill_ids,
            job_skills,
        )

        # Do not return jobs with zero overlap.
        if not matched_skills:
            continue

        result = {
            "job_id": job_id,
            "title": first_row["title"],
            "company_name": first_row["company_name"],
            "location": first_row["location"],
            "source_url": first_row["source_url"],
            "match_score": round(score, 4),
            "matched_skill_count": len(
                matched_skills
            ),
            "total_job_skills": len(job_skills),
            "matched_skills": matched_skills,
        }

        results.append(result)

    results.sort(
        key=lambda item: (
            item["match_score"],
            item["matched_skill_count"],
        ),
        reverse=True,
    )

    return results[:top_k]