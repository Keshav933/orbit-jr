import html
import re
from collections import defaultdict

from backend.app.database import get_connection
from backend.app.ranking import rank_jobs


def clean_job_text(text):
    """
    Clean HTML entities and extra whitespace
    from job descriptions.
    """

    if not text:
        return ""

    text = html.unescape(str(text))

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def get_profile_skill_ids(profile_id):
    """
    Get the candidate's resume-derived skill IDs.
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT skill_id
            FROM profile_skills
            WHERE profile_id = %s
              AND source = 'resume'
            """,
            (profile_id,),
        )

        rows = cursor.fetchall()

        return {
            row[0]
            for row in rows
        }

    finally:
        cursor.close()
        connection.close()


def get_job_details(job_id):
    """
    Get the complete job description and metadata.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                id,
                title,
                description
            FROM jobs
            WHERE id = %s
            """,
            (job_id,),
        )

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


def get_job_skills(job_id):
    """
    Get all extracted skills belonging to a job.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                js.skill_id,
                js.importance,
                js.requirement_type,
                s.name AS skill_name
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

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def get_skill_aliases(skill_ids):
    """
    Get aliases for the required skill IDs.
    """

    if not skill_ids:
        return {}

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        placeholders = ", ".join(
            ["%s"] * len(skill_ids)
        )

        query = f"""
            SELECT
                skill_id,
                alias
            FROM skill_aliases
            WHERE skill_id IN ({placeholders})
            ORDER BY
                LENGTH(alias) DESC
        """

        cursor.execute(
            query,
            tuple(skill_ids),
        )

        rows = cursor.fetchall()

        aliases = defaultdict(list)

        for row in rows:
            aliases[row["skill_id"]].append(
                row["alias"]
            )

        return dict(aliases)

    finally:
        cursor.close()
        connection.close()


def find_text_evidence(
    text,
    aliases,
):
    """
    Find a concrete piece of job text supporting
    a detected skill.

    Returns:
        {
            "evidence_text": "...",
            "matched_alias": "...",
            "evidence_strength": 1.0
        }

        or None if no occurrence is found.
    """

    if not text:
        return None

    text = clean_job_text(text)

    # Longer aliases first.
    aliases = sorted(
        aliases,
        key=len,
        reverse=True,
    )

    for alias in aliases:

        alias = str(alias).strip()

        if not alias:
            continue

        pattern = re.escape(alias)

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        start = match.start()
        end = match.end()

        # Keep the evidence reasonably short.
        context_start = max(
            0,
            start - 90,
        )

        context_end = min(
            len(text),
            end + 110,
        )

        evidence_text = text[
            context_start:context_end
        ]

        # Clean the context boundaries.
        evidence_text = evidence_text.strip()

        return {
            "evidence_text": evidence_text,
            "matched_alias": alias,
            "evidence_strength": 1.0,
        }

    return None


def analyze_job(profile_id, job_id):
    """
    Analyze one job against one candidate.

    Returns:
        matched skills
        skill gaps
        evidence
        coverage
    """

    profile_skill_ids = get_profile_skill_ids(
        profile_id
    )

    job = get_job_details(
        job_id
    )

    if not job:
        return None

    job_skills = get_job_skills(
        job_id
    )

    if not job_skills:
        return {
            "job_id": job_id,
            "title": job["title"],
            "matched_skills": [],
            "skill_gaps": [],
            "required_gaps": [],
            "preferred_gaps": [],
            "skill_coverage": 0.0,
            "evidence": [],
        }

    skill_ids = {
        skill["skill_id"]
        for skill in job_skills
    }

    aliases = get_skill_aliases(
        skill_ids
    )

    matched_skills = []
    skill_gaps = []
    required_gaps = []
    preferred_gaps = []
    evidence = []

    for skill in job_skills:

        skill_id = skill["skill_id"]

        is_matched = (
            skill_id in profile_skill_ids
        )

        skill_result = {
            "skill_id": skill_id,
            "skill_name": skill["skill_name"],
            "requirement_type": skill[
                "requirement_type"
            ],
            "importance": float(
                skill["importance"] or 1.0
            ),
        }

        skill_evidence = find_text_evidence(
            job["description"],
            aliases.get(skill_id, []),
        )

        if is_matched:

            matched_skills.append(
                skill_result
            )

            if skill_evidence:
                evidence.append(
                    {
                        "skill_id": skill_id,
                        "skill_name": skill[
                            "skill_name"
                        ],
                        "evidence_type": "job_text",
                        "evidence_text": (
                            skill_evidence[
                                "evidence_text"
                            ]
                        ),
                        "matched_alias": (
                            skill_evidence[
                                "matched_alias"
                            ]
                        ),
                        "evidence_strength": (
                            skill_evidence[
                                "evidence_strength"
                            ]
                        ),
                    }
                )

        else:

            skill_gaps.append(
                skill_result
            )

            if (
                skill["requirement_type"]
                == "required"
            ):
                required_gaps.append(
                    skill_result
                )
            else:
                preferred_gaps.append(
                    skill_result
                )

    total_skills = len(
        job_skills
    )

    matched_count = len(
        matched_skills
    )

    if total_skills > 0:
        skill_coverage = (
            matched_count / total_skills
        )
    else:
        skill_coverage = 0.0

    return {
        "job_id": job_id,
        "title": job["title"],
        "matched_skills": matched_skills,
        "skill_gaps": skill_gaps,
        "required_gaps": required_gaps,
        "preferred_gaps": preferred_gaps,
        "skill_coverage": round(
            skill_coverage,
            4,
        ),
        "evidence": evidence,
    }


def get_ranked_jobs_with_explanations(
    profile_id,
    retrieval_k=50,
    top_k=10,
):
    """
    Get ranked jobs and attach evidence + skill gaps.
    """

    ranked_jobs = rank_jobs(
        profile_id,
        retrieval_k=retrieval_k,
        top_k=top_k,
    )

    results = []

    for job in ranked_jobs:

        analysis = analyze_job(
            profile_id,
            job["job_id"],
        )

        if analysis:
            job["matched_skills"] = (
                analysis["matched_skills"]
            )

            job["skill_gaps"] = (
                analysis["skill_gaps"]
            )

            job["required_gaps"] = (
                analysis["required_gaps"]
            )

            job["preferred_gaps"] = (
                analysis["preferred_gaps"]
            )

            job["evidence"] = (
                analysis["evidence"]
            )

            job["evidence_count"] = len(
                analysis["evidence"]
            )

            job["evidence_coverage"] = (
                round(
                    len(analysis["evidence"])
                    / max(
                        len(
                            analysis[
                                "matched_skills"
                            ]
                        ),
                        1,
                    ),
                    4,
                )
            )

        results.append(job)

    return results