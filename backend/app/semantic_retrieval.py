import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

from backend.app.database import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

INDEX_FILE = Path(
    "data/indexes/jobs.faiss"
)

METADATA_FILE = Path(
    "data/indexes/jobs_metadata.json"
)


def get_profile_text(profile_id):
    """
    Build a textual query from the candidate's profile skills.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
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

        rows = cursor.fetchall()

        skills = [
            row["skill_name"]
            for row in rows
        ]

        if not skills:
            return ""

        return (
            "Candidate skills: "
            + ", ".join(skills)
        )

    finally:
        cursor.close()
        connection.close()


def load_index():
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
        encoding="utf-8"
    ) as file:
        metadata = json.load(file)

    return index, metadata


def semantic_search(
    profile_id,
    top_k=10
):
    """
    Retrieve jobs using semantic similarity.
    """

    query_text = get_profile_text(
        profile_id
    )

    if not query_text:
        return []

    index, metadata = load_index()

    model = SentenceTransformer(
        MODEL_NAME
    )

    query_embedding = model.encode(
        [query_text],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    scores, indices = index.search(
        query_embedding,
        top_k
    )

    results = []

    for score, index_position in zip(
        scores[0],
        indices[0]
    ):

        if index_position < 0:
            continue

        job = metadata[
            int(index_position)
        ]

        results.append(
            {
                "job_id": job["job_id"],
                "title": job["title"],
                "company_name": job["company_name"],
                "location": job["location"],
                "source_url": job["source_url"],
                "semantic_score": round(
                    float(score),
                    4
                ),
            }
        )

    return results