import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

from backend.app.database import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INDEX_FILE = PROJECT_ROOT / "data" / "indexes" / "jobs.faiss"
METADATA_FILE = PROJECT_ROOT / "data" / "indexes" / "jobs_metadata.json"

LIVE_INDEX_FILE = PROJECT_ROOT / "data" / "indexes" / "live_jobs.faiss"
LIVE_METADATA_FILE = PROJECT_ROOT / "data" / "indexes" / "live_jobs_metadata.json"


# Initial research baseline weight.
LEXICAL_WEIGHT = 0.5
SEMANTIC_WEIGHT = 0.5


LIVE_SOURCE_TYPES = (
    "jobicy",
    "himalayas",
    "remoteok",
)


@lru_cache(maxsize=1)
def load_model():
    """
    Load the embedding model once per Python process.
    """

    return SentenceTransformer(
        MODEL_NAME
    )


def get_profile_skills(profile_id):
    """
    Get skills extracted from the candidate resume.
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


def get_job_skills():
    """
    Get Role Radar jobs and active live-source jobs
    together with their extracted skills.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    placeholders = ", ".join(
        ["%s"] * len(LIVE_SOURCE_TYPES)
    )

    try:
        cursor.execute(
            f"""
            SELECT
                j.id AS job_id,
                j.title,
                j.company_name,
                j.location,
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
               OR (
                    j.source_type IN ({placeholders})
                    AND j.is_active = 1
               )
            ORDER BY j.id
            """,
            LIVE_SOURCE_TYPES,
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def calculate_lexical_scores(
    profile_skill_ids,
    rows,
):
    """
    Calculate the lexical score for every job.
    """

    jobs = defaultdict(list)

    for row in rows:
        jobs[row["job_id"]].append(row)

    scores = {}

    for job_id, job_rows in jobs.items():

        total_weight = 0.0
        matched_weight = 0.0

        matched_skills = []

        for skill in job_rows:

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

        if total_weight > 0:
            lexical_score = (
                matched_weight / total_weight
            )
        else:
            lexical_score = 0.0

        first_row = job_rows[0]

        scores[job_id] = {
            "job_id": job_id,
            "title": first_row["title"],
            "company_name": first_row["company_name"],
            "location": first_row["location"],
            "source_url": first_row["source_url"],
            "lexical_score": lexical_score,
            "matched_skills": matched_skills,
            "total_job_skills": len(job_rows),
        }

    return scores


def create_profile_text(profile_skills):
    """
    Convert candidate skills into semantic-query text.
    """

    skill_names = [
        skill["skill_name"]
        for skill in profile_skills
    ]

    if not skill_names:
        return ""

    return (
        "Candidate skills: "
        + ", ".join(skill_names)
    )


def load_index_and_metadata():
    """
    Load the existing combined semantic index and metadata.
    """

    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {INDEX_FILE}"
        )

    if not METADATA_FILE.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {METADATA_FILE}"
        )

    index = faiss.read_index(
        str(INDEX_FILE)
    )

    with METADATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        metadata = json.load(file)

    return index, metadata


def load_live_index_and_metadata():
    """
    Load the frequently refreshed live-job semantic index.

    The live index is optional so the existing combined index can still be
    used before the first live-index build.
    """

    if not LIVE_INDEX_FILE.exists():
        return None, None

    if not LIVE_METADATA_FILE.exists():
        return None, None

    index = faiss.read_index(
        str(LIVE_INDEX_FILE)
    )

    with LIVE_METADATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        metadata = json.load(file)

    return index, metadata


def convert_cosine_to_zero_one(score):
    """
    Convert cosine similarity [-1, 1]
    into a [0, 1] range.

    This makes it easier to combine with
    the lexical score, which is already [0, 1].
    """

    value = (float(score) + 1.0) / 2.0

    return max(
        0.0,
        min(1.0, value)
    )


def retrieve_hybrid_jobs(
    profile_id,
    top_k=10,
):
    """
    Retrieve jobs using:

        hybrid_score =
            0.5 * lexical_score
            + 0.5 * semantic_score
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

    job_rows = get_job_skills()

    lexical_results = calculate_lexical_scores(
        profile_skill_ids,
        job_rows,
    )

    if not lexical_results:
        return []

    index, metadata = (
        load_index_and_metadata()
    )

    profile_text = create_profile_text(
        profile_skills
    )

    model = load_model()

    query_embedding = model.encode(
        [profile_text],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    # The original combined index is retained for backward compatibility.
    # It may contain old live-job embeddings, but the live index below
    # overwrites those scores with freshly generated live embeddings.
    scores, indices = index.search(
        query_embedding,
        index.ntotal,
    )

    semantic_scores = {}

    for score, index_position in zip(
        scores[0],
        indices[0],
    ):

        if index_position < 0:
            continue

        job = metadata[
            int(index_position)
        ]

        job_id = job["job_id"]

        semantic_scores[job_id] = (
            convert_cosine_to_zero_one(score)
        )

    # The live index contains only active Jobicy/Himalayas/Remote OK jobs.
    # Searching it separately lets newly synchronized jobs enter retrieval
    # immediately and gives previously indexed live jobs fresh embeddings.
    live_index, live_metadata = (
        load_live_index_and_metadata()
    )

    if live_index is not None and live_metadata:
        live_scores, live_indices = live_index.search(
            query_embedding,
            live_index.ntotal,
        )

        for score, index_position in zip(
            live_scores[0],
            live_indices[0],
        ):

            if index_position < 0:
                continue

            job = live_metadata[
                int(index_position)
            ]

            job_id = job["job_id"]

            semantic_scores[job_id] = (
                convert_cosine_to_zero_one(score)
            )

    results = []

    for job_id, job in lexical_results.items():

        lexical_score = job["lexical_score"]

        semantic_score = semantic_scores.get(
            job_id,
            0.0,
        )

        hybrid_score = (
            LEXICAL_WEIGHT * lexical_score
            + SEMANTIC_WEIGHT * semantic_score
        )

        result = {
            "job_id": job["job_id"],
            "title": job["title"],
            "company_name": job["company_name"],
            "location": job["location"],
            "source_url": job["source_url"],
            "lexical_score": round(
                lexical_score,
                4,
            ),
            "semantic_score": round(
                semantic_score,
                4,
            ),
            "hybrid_score": round(
                hybrid_score,
                4,
            ),
            "matched_skill_count": len(
                job["matched_skills"]
            ),
            "total_job_skills": job[
                "total_job_skills"
            ],
            "matched_skills": job[
                "matched_skills"
            ],
        }

        results.append(result)

    # Keep the candidate-grounded baseline:
    # require at least one lexical skill match.
    results = [
        result
        for result in results
        if result["matched_skill_count"] > 0
    ]

    results.sort(
        key=lambda item: item["hybrid_score"],
        reverse=True,
    )

    return results[:top_k]
