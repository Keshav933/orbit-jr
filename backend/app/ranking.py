import re

from backend.app.database import get_connection
from backend.app.hybrid_retrieval import (
    retrieve_hybrid_jobs,
)


# Initial ranking weights.
#
# These are baseline experimental weights.
# They are not learned model coefficients.
HYBRID_WEIGHT = 0.40
SKILL_COVERAGE_WEIGHT = 0.20
EXPERIENCE_WEIGHT = 0.15
ROLE_WEIGHT = 0.10
SENIORITY_WEIGHT = 0.05
LOCATION_WEIGHT = 0.05
MARKET_WEIGHT = 0.05


LIVE_SOURCE_TYPES = (
    "jobicy",
    "himalayas",
    "remoteok",
)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "developer",
    "engineer",
    "for",
    "in",
    "of",
    "software",
    "the",
    "to",
}


def normalize_text(text):
    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9+#.\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def get_keywords(text):
    text = normalize_text(text)

    words = text.split()

    keywords = set()

    for word in words:

        if word in STOP_WORDS:
            continue

        if len(word) < 2:
            continue

        keywords.add(word)

    return keywords


def calculate_role_score(
    preferred_role,
    job_title,
    role_family_hint,
):
    """
    Compare candidate preferred role
    with the job title and role family.
    """

    profile_words = get_keywords(
        preferred_role
    )

    if not profile_words:
        return 0.5

    job_words = (
        get_keywords(job_title)
        | get_keywords(role_family_hint)
    )

    if not job_words:
        return 0.0

    overlap = (
        profile_words & job_words
    )

    return len(overlap) / len(
        profile_words
    )


def infer_candidate_seniority(
    experience_years
):
    """
    Simple baseline seniority estimation.
    """

    years = float(
        experience_years or 0
    )

    if years < 1:
        return "entry"

    if years < 3:
        return "junior"

    if years < 5:
        return "mid"

    if years < 8:
        return "senior"

    return "lead"


def normalize_seniority(value):
    if not value:
        return ""

    value = value.lower()

    if (
        "intern" in value
        or "trainee" in value
    ):
        return "entry"

    if (
        "entry" in value
        or "fresher" in value
        or "junior" in value
    ):
        return "junior"

    if (
        "mid" in value
        or "associate" in value
    ):
        return "mid"

    if (
        "senior" in value
        or "sr." in value
        or "sr " in value
    ):
        return "senior"

    if (
        "lead" in value
        or "principal" in value
        or "staff" in value
    ):
        return "lead"

    return ""


def calculate_seniority_score(
    candidate_seniority,
    job_seniority,
):
    """
    Compare candidate and job seniority.
    """

    job_level = normalize_seniority(
        job_seniority
    )

    if not job_level:
        return 0.5

    levels = {
        "entry": 0,
        "junior": 1,
        "mid": 2,
        "senior": 3,
        "lead": 4,
    }

    candidate_level = levels.get(
        candidate_seniority,
        0,
    )

    required_level = levels.get(
        job_level,
        0,
    )

    difference = abs(
        candidate_level - required_level
    )

    if difference == 0:
        return 1.0

    if difference == 1:
        return 0.7

    if difference == 2:
        return 0.4

    return 0.2


def calculate_experience_score(
    candidate_years,
    experience_min,
    experience_max,
):
    """
    Compare candidate experience
    with job experience range.
    """

    candidate_years = float(
        candidate_years or 0
    )

    minimum = (
        float(experience_min)
        if experience_min is not None
        else None
    )

    maximum = (
        float(experience_max)
        if experience_max is not None
        else None
    )

    if minimum is None and maximum is None:
        return 0.5

    if (
        minimum is not None
        and candidate_years < minimum
    ):
        difference = (
            minimum - candidate_years
        )

        if difference <= 1:
            return 0.5

        if difference <= 2:
            return 0.3

        return 0.0

    if (
        maximum is not None
        and candidate_years > maximum
    ):
        return 0.5

    return 1.0


def calculate_location_score(
    profile_location,
    job_location,
    is_remote,
):
    """
    Simple location compatibility baseline.
    """

    if is_remote:
        return 1.0

    profile_location = normalize_text(
        profile_location
    )

    job_location = normalize_text(
        job_location
    )

    if not profile_location or not job_location:
        return 0.5

    profile_words = get_keywords(
        profile_location
    )

    job_words = get_keywords(
        job_location
    )

    if not profile_words or not job_words:
        return 0.5

    if profile_words & job_words:
        return 1.0

    return 0.0


def get_profile(profile_id):
    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    try:
        cursor.execute(
            """
            SELECT
                id,
                user_id,
                experience_years,
                location,
                preferred_role
            FROM profiles
            WHERE id = %s
            """,
            (profile_id,),
        )

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


def get_job_metadata():
    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    placeholders = ", ".join(
        ["%s"] * len(LIVE_SOURCE_TYPES)
    )

    try:
        cursor.execute(
            f"""
            SELECT
                id,
                source_type,
                application_url,
                seniority_level,
                employment_type,
                job_function,
                role_family_hint,
                domain_hint,
                experience_min,
                experience_max,
                is_remote,
                location
            FROM jobs
            WHERE source = 'role-radar'
               OR (
                    source_type IN ({placeholders})
                    AND is_active = 1
               )
            """,
            LIVE_SOURCE_TYPES,
        )

        rows = cursor.fetchall()

        return {
            row["id"]: row
            for row in rows
        }

    finally:
        cursor.close()
        connection.close()


def get_market_stats():
    """
    Load corpus-level market demand scores.
    """

    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    try:
        cursor.execute(
            """
            SELECT
                skill_id,
                market_score
            FROM skill_market_stats
            """
        )

        rows = cursor.fetchall()

        return {
            row["skill_id"]: float(
                row["market_score"]
            )
            for row in rows
        }

    finally:
        cursor.close()
        connection.close()


def calculate_market_score(
    profile_skill_ids,
    job_skills,
    market_stats,
):
    """
    Calculate the market demand of skills
    matched by this candidate.

    Only candidate-matched skills contribute.
    """

    weighted_market = 0.0
    matched_weight = 0.0

    for skill in job_skills:

        if skill["skill_id"] not in profile_skill_ids:
            continue

        importance = float(
            skill["importance"] or 1.0
        )

        if (
            skill["requirement_type"]
            == "preferred"
        ):
            importance *= 0.5

        market_score = market_stats.get(
            skill["skill_id"],
            0.0,
        )

        weighted_market += (
            market_score * importance
        )

        matched_weight += importance

    if matched_weight == 0:
        return 0.0

    return weighted_market / matched_weight


def calculate_final_score(
    hybrid_score,
    skill_coverage,
    experience_score,
    role_score,
    seniority_score,
    location_score,
    market_score,
):
    return (
        HYBRID_WEIGHT * hybrid_score
        + SKILL_COVERAGE_WEIGHT * skill_coverage
        + EXPERIENCE_WEIGHT * experience_score
        + ROLE_WEIGHT * role_score
        + SENIORITY_WEIGHT * seniority_score
        + LOCATION_WEIGHT * location_score
        + MARKET_WEIGHT * market_score
    )


def get_all_job_skills():
    """
    Get job skills grouped by job ID.
    """

    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    placeholders = ", ".join(
        ["%s"] * len(LIVE_SOURCE_TYPES)
    )

    try:
        cursor.execute(
            f"""
            SELECT
                js.job_id,
                js.skill_id,
                js.importance,
                js.requirement_type
            FROM job_skills js
            JOIN jobs j
                ON j.id = js.job_id
            WHERE j.source = 'role-radar'
               OR (
                    j.source_type IN ({placeholders})
                    AND j.is_active = 1
               )
            """,
            LIVE_SOURCE_TYPES,
        )

        rows = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    grouped = {}

    for row in rows:

        job_id = row["job_id"]

        if job_id not in grouped:
            grouped[job_id] = []

        grouped[job_id].append(row)

    return grouped


def rank_jobs(
    profile_id,
    retrieval_k=50,
    top_k=10,
):
    """
    Retrieve a candidate pool and rerank it
    using relevance, compatibility and market signals.
    """

    profile = get_profile(
        profile_id
    )

    if not profile:
        return []

    candidates = retrieve_hybrid_jobs(
        profile_id,
        top_k=retrieval_k,
    )

    if not candidates:
        return []

    job_metadata = get_job_metadata()

    market_stats = get_market_stats()

    all_job_skills = get_all_job_skills()

    candidate_experience = (
        profile["experience_years"] or 0
    )

    candidate_seniority = (
        infer_candidate_seniority(
            candidate_experience
        )
    )

    profile_skill_ids = set(
        get_profile_skill_rows(
            profile_id
        )
    )

    total_profile_skills = len(
        profile_skill_ids
    )

    results = []

    for job in candidates:

        job_id = job["job_id"]

        metadata = job_metadata.get(
            job_id,
            {},
        )

        job_skills = all_job_skills.get(
            job_id,
            [],
        )

        if total_profile_skills > 0:
            skill_coverage = (
                job["matched_skill_count"]
                / total_profile_skills
            )
        else:
            skill_coverage = 0.0

        skill_coverage = min(
            skill_coverage,
            1.0,
        )

        experience_score = (
            calculate_experience_score(
                candidate_experience,
                metadata.get(
                    "experience_min"
                ),
                metadata.get(
                    "experience_max"
                ),
            )
        )

        role_score = calculate_role_score(
            profile["preferred_role"],
            job["title"],
            metadata.get(
                "role_family_hint"
            ),
        )

        seniority_score = (
            calculate_seniority_score(
                candidate_seniority,
                metadata.get(
                    "seniority_level"
                ),
            )
        )

        location_score = (
            calculate_location_score(
                profile["location"],
                metadata.get(
                    "location"
                ),
                metadata.get(
                    "is_remote"
                ),
            )
        )

        market_score = calculate_market_score(
            profile_skill_ids,
            job_skills,
            market_stats,
        )

        final_score = calculate_final_score(
            job["hybrid_score"],
            skill_coverage,
            experience_score,
            role_score,
            seniority_score,
            location_score,
            market_score,
        )

        result = {
            "job_id": job_id,
            "title": job["title"],
            "company_name": job["company_name"],
            "location": job["location"],
            "source_url": job["source_url"],
            "source_type": metadata.get("source_type"),
            "application_url": metadata.get("application_url"),
            "hybrid_score": job[
                "hybrid_score"
            ],
            "skill_coverage": round(
                skill_coverage,
                4,
            ),
            "experience_score": round(
                experience_score,
                4,
            ),
            "role_score": round(
                role_score,
                4,
            ),
            "seniority_score": round(
                seniority_score,
                4,
            ),
            "location_score": round(
                location_score,
                4,
            ),
            "market_score": round(
                market_score,
                4,
            ),
            "final_score": round(
                final_score,
                4,
            ),
            "matched_skill_count": job[
                "matched_skill_count"
            ],
            "total_job_skills": job[
                "total_job_skills"
            ],
            "matched_skills": job[
                "matched_skills"
            ],
        }

        results.append(result)

    results.sort(
        key=lambda item: item["final_score"],
        reverse=True,
    )

    return results[:top_k]


def get_profile_skill_rows(profile_id):
    """
    Get candidate skill IDs once.
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

        return [
            row[0]
            for row in cursor.fetchall()
        ]

    finally:
        cursor.close()
        connection.close()
