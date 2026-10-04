from datetime import datetime

from backend.app.database import get_connection
from backend.app.ranking import rank_jobs
from backend.app.evidence import analyze_job
from backend.app.confidence import (
    calculate_confidence,
    get_confidence_label,
)


def get_job_filter_metadata(job_ids):
    """
    Load metadata needed for filtering and sorting.
    """

    if not job_ids:
        return {}

    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    try:
        placeholders = ", ".join(
            ["%s"] * len(job_ids)
        )

        query = f"""
            SELECT
                id,
                is_remote,
                job_function,
                role_family_hint,
                employment_type,
                experience_min,
                experience_max,
                posted_date,
                source_type
            FROM jobs
            WHERE id IN ({placeholders})
        """

        cursor.execute(
            query,
            tuple(job_ids),
        )

        rows = cursor.fetchall()

        return {
            row["id"]: row
            for row in rows
        }

    finally:
        cursor.close()
        connection.close()


def normalize_experience_level(
    experience_min,
    experience_max,
):
    """
    Convert a job's experience range into
    a simple experience level for filtering.
    """

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
        return "unknown"

    if minimum is not None and minimum < 1:
        return "entry"

    if minimum is not None and minimum < 3:
        return "junior"

    if minimum is not None and minimum < 5:
        return "mid"

    return "senior"


def matches_filters(
    job,
    metadata,
    search="",
    location="",
    role="",
    remote_only=False,
    min_score=0.0,
    experience_level="",
    employment_type="",
):
    """
    Decide whether one job should be kept.
    """

    search = (
        search or ""
    ).strip().lower()

    location = (
        location or ""
    ).strip().lower()

    role = (
        role or ""
    ).strip().lower()

    experience_level = (
        experience_level or ""
    ).strip().lower()

    employment_type = (
        employment_type or ""
    ).strip().lower()

    # Minimum recommendation score.
    if float(
        job.get(
            "final_score",
            0.0,
        )
    ) < min_score:
        return False

    # Search job title or company.
    if search:
        title = str(
            job.get("title") or ""
        ).lower()

        company = str(
            job.get("company_name") or ""
        ).lower()

        if (
            search not in title
            and search not in company
        ):
            return False

    # Location.
    if location:
        job_location = str(
            job.get("location") or ""
        ).lower()

        if location not in job_location:
            return False

    # Remote only.
    if remote_only:
        if not metadata.get(
            "is_remote",
            False,
        ):
            return False

    # Role/category.
    if role:
        title = str(
            job.get("title") or ""
        ).lower()

        job_function = str(
            metadata.get(
                "job_function"
            ) or ""
        ).lower()

        role_family = str(
            metadata.get(
                "role_family_hint"
            ) or ""
        ).lower()

        if (
            role not in title
            and role not in job_function
            and role not in role_family
        ):
            return False

    # Experience level.
    if experience_level:
        job_level = normalize_experience_level(
            metadata.get(
                "experience_min"
            ),
            metadata.get(
                "experience_max"
            ),
        )

        if job_level != experience_level:
            return False

    # Employment type.
    if employment_type:
        value = str(
            metadata.get(
                "employment_type"
            ) or ""
        ).lower()

        if employment_type not in value:
            return False

    return True


def _posted_timestamp(value):
    """
    Convert a posted date into a sortable timestamp.
    """

    if not value:
        return 0.0

    if hasattr(value, "timestamp"):
        try:
            return float(
                value.timestamp()
            )
        except (
            TypeError,
            ValueError,
            OSError,
        ):
            return 0.0

    try:
        return datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        ).timestamp()

    except (
        TypeError,
        ValueError,
        OSError,
    ):
        return 0.0


def _is_live_job(item):
    """
    Identify jobs coming from the live/fresh sources.
    """

    return str(
        item.get("source_type") or ""
    ).lower() in {
        "jobicy",
        "himalayas",
        "remoteok",
    }


def sort_recommendations(
    recommendations,
    sort_by,
):
    """
    Sort recommendation results.

    recent:
        1. Live jobs first.
        2. Newest live jobs first.
        3. Match score as tie-breaker.

    skill_match:
        Highest skill match first.

    best_match:
        Highest recommendation score first.
    """

    if sort_by == "skill_match":

        recommendations.sort(
            key=lambda item: (
                float(
                    item.get(
                        "skill_coverage",
                        0.0,
                    )
                ),
                int(
                    item.get(
                        "matched_skill_count",
                        0,
                    )
                ),
                float(
                    item.get(
                        "final_score",
                        0.0,
                    )
                ),
            ),
            reverse=True,
        )

    elif sort_by == "recent":

        recommendations.sort(
            key=lambda item: (
                _is_live_job(item),

                _posted_timestamp(
                    item.get(
                        "posted_date"
                    )
                ),

                float(
                    item.get(
                        "final_score",
                        0.0,
                    )
                ),
            ),
            reverse=True,
        )

    else:

        recommendations.sort(
            key=lambda item: float(
                item.get(
                    "final_score",
                    0.0,
                )
            ),
            reverse=True,
        )

    return recommendations


def get_recommendations(
    profile_id,
    top_k=20,
    search="",
    location="",
    role="",
    remote_only=False,
    min_score=0.0,
    experience_level="",
    employment_type="",
    sort_by="recent",
    page=1,
    page_size=20,
):
    """
    Get filtered and sorted job recommendations.

    Important performance design:

    - Ranking/filtering/sorting happens before pagination.
    - Only the requested page is enriched with expensive
      evidence/skill-gap analysis.
    - Maximum page size is 20.
    """

    # Kept for compatibility with existing API callers.
    _ = top_k

    # Validate page.
    try:
        page = max(
            1,
            int(page),
        )
    except (
        TypeError,
        ValueError,
    ):
        page = 1

    # Validate page size.
    try:
        page_size = max(
            1,
            min(
                20,
                int(page_size),
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        page_size = 20

    # Keep score inside [0, 1].
    if min_score < 0:
        min_score = 0.0

    if min_score > 1:
        min_score = 1.0

    valid_sort_values = {
        "best_match",
        "skill_match",
        "recent",
    }

    if sort_by not in valid_sort_values:
        sort_by = "best_match"

    valid_experience_levels = {
        "entry",
        "junior",
        "mid",
        "senior",
    }

    if (
        experience_level
        and experience_level
        not in valid_experience_levels
    ):
        experience_level = ""

    # ---------------------------------------------------------
    # Determine the size of the current candidate corpus.
    # ---------------------------------------------------------

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(DISTINCT j.id)
            FROM jobs j
            JOIN job_skills js
              ON js.job_id = j.id
            WHERE j.source = 'role-radar'
               OR (
                    j.source_type IN (
                        'jobicy',
                        'himalayas',
                        'remoteok'
                    )
                    AND j.is_active = 1
               )
            """
        )

        candidate_pool_size = int(
            cursor.fetchone()[0] or 0
        )

    finally:
        cursor.close()
        connection.close()

    candidate_pool_size = max(
        candidate_pool_size,
        1,
    )

    # ---------------------------------------------------------
    # Rank the candidate pool.
    # ---------------------------------------------------------

    ranked_jobs = rank_jobs(
        profile_id,
        retrieval_k=candidate_pool_size,
        top_k=candidate_pool_size,
    )

    if not ranked_jobs:
        return {
            "items": [],
            "total_count": 0,
            "page": 1,
            "page_size": page_size,
            "total_pages": 0,
            "has_more": False,
        }

    # ---------------------------------------------------------
    # Load metadata for filtering.
    # ---------------------------------------------------------

    job_ids = [
        job["job_id"]
        for job in ranked_jobs
    ]

    metadata = get_job_filter_metadata(
        job_ids
    )

    filtered_jobs = []

    # ---------------------------------------------------------
    # Apply filters.
    # ---------------------------------------------------------

    for job in ranked_jobs:

        job_metadata = metadata.get(
            job["job_id"],
            {},
        )

        if not matches_filters(
            job,
            job_metadata,
            search=search,
            location=location,
            role=role,
            remote_only=remote_only,
            min_score=min_score,
            experience_level=experience_level,
            employment_type=employment_type,
        ):
            continue

        job["is_remote"] = bool(
            job_metadata.get(
                "is_remote",
                False,
            )
        )

        job["job_function"] = (
            job_metadata.get(
                "job_function"
            )
        )

        job["role_family_hint"] = (
            job_metadata.get(
                "role_family_hint"
            )
        )

        job["employment_type"] = (
            job_metadata.get(
                "employment_type"
            )
        )

        job["experience_min"] = (
            job_metadata.get(
                "experience_min"
            )
        )

        job["experience_max"] = (
            job_metadata.get(
                "experience_max"
            )
        )

        job["posted_date"] = (
            job_metadata.get(
                "posted_date"
            )
        )

        job["source_type"] = (
            job_metadata.get(
                "source_type"
            )
        )

        filtered_jobs.append(job)

    # ---------------------------------------------------------
    # IMPORTANT:
    # Sort the complete filtered list BEFORE pagination.
    #
    # This guarantees:
    #
    # Page 1 → first 20
    # Page 2 → next 20
    # Page 3 → next 20
    #
    # while keeping exactly the same global order.
    # ---------------------------------------------------------

    sort_recommendations(
        filtered_jobs,
        sort_by,
    )

    total_count = len(
        filtered_jobs
    )

    if total_count == 0:
        return {
            "items": [],
            "total_count": 0,
            "page": 1,
            "page_size": page_size,
            "total_pages": 0,
            "has_more": False,
        }

    total_pages = (
        total_count
        + page_size
        - 1
    ) // page_size

    # Protect against requesting a page beyond the last page.
    page = min(
        page,
        total_pages,
    )

    start = (
        page - 1
    ) * page_size

    end = (
        start
        + page_size
    )

    # ---------------------------------------------------------
    # ONLY THESE JOBS RECEIVE EXPENSIVE EVIDENCE ANALYSIS.
    #
    # This is the important ECONNRESET fix.
    # ---------------------------------------------------------

    page_jobs = filtered_jobs[
        start:end
    ]

    recommendations = []

    for job in page_jobs:

        analysis = analyze_job(
            profile_id,
            job["job_id"],
        )

        if analysis:

            job["matched_skills"] = (
                analysis[
                    "matched_skills"
                ]
            )

            job["skill_gaps"] = (
                analysis[
                    "skill_gaps"
                ]
            )

            job["required_gaps"] = (
                analysis[
                    "required_gaps"
                ]
            )

            job["preferred_gaps"] = (
                analysis[
                    "preferred_gaps"
                ]
            )

            job["evidence"] = (
                analysis[
                    "evidence"
                ]
            )

            job["evidence_count"] = len(
                analysis[
                    "evidence"
                ]
            )

            job[
                "evidence_coverage"
            ] = round(
                len(
                    analysis[
                        "evidence"
                    ]
                )
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

        else:

            job["matched_skills"] = (
                job.get(
                    "matched_skills",
                    [],
                )
            )

            job["skill_gaps"] = []

            job["required_gaps"] = []

            job["preferred_gaps"] = []

            job["evidence"] = []

            job["evidence_count"] = 0

            job["evidence_coverage"] = 0.0

        confidence = (
            calculate_confidence(
                job
            )
        )

        job["confidence"] = (
            confidence
        )

        job["confidence_label"] = (
            get_confidence_label(
                confidence
            )
        )

        recommendations.append(
            job
        )

    # ---------------------------------------------------------
    # Return ONLY the requested page.
    # ---------------------------------------------------------

    return {
        "items": recommendations,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": (
            page < total_pages
        ),
    }