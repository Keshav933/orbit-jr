import json
import sys
from pathlib import Path

import faiss
import numpy as np

# Add project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import get_connection
from backend.app.hybrid_retrieval import load_model


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

INDEX_DIR = Path("data/indexes")
INDEX_FILE = INDEX_DIR / "jobs.faiss"
METADATA_FILE = INDEX_DIR / "jobs_metadata.json"

LIVE_SOURCE_TYPES = (
    "jobicy",
    "himalayas",
    "remoteok",
)


def get_jobs():
    """
    Get Role Radar jobs and active jobs from the live sources.
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
                id,
                title,
                company_name,
                location,
                description,
                source_url,
                source,
                source_type
            FROM jobs
            WHERE source = 'role-radar'
               OR (
                    source_type IN ({placeholders})
                    AND is_active = 1
               )
            ORDER BY id
            """,
            LIVE_SOURCE_TYPES,
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def create_job_text(job):
    """
    Create the text representation used by the embedding model.
    """

    title = job["title"] or ""
    company = job["company_name"] or ""
    location = job["location"] or ""
    description = job["description"] or ""

    return (
        f"Job title: {title}\n"
        f"Company: {company}\n"
        f"Location: {location}\n"
        f"Description: {description}"
    )


def main():
    INDEX_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    jobs = get_jobs()

    if not jobs:
        print("No eligible jobs found.")
        return

    role_radar_count = sum(
        1
        for job in jobs
        if job["source"] == "role-radar"
    )

    live_counts = {
        source_type: 0
        for source_type in LIVE_SOURCE_TYPES
    }

    for job in jobs:
        source_type = job["source_type"]

        if source_type in live_counts:
            live_counts[source_type] += 1

    print(f"Total jobs found: {len(jobs)}")
    print(f"Role Radar jobs: {role_radar_count}")

    print("Active live jobs:")

    for source_type in LIVE_SOURCE_TYPES:
        print(
            f"  {source_type}: "
            f"{live_counts[source_type]}"
        )

    print()
    print(f"Loading model: {MODEL_NAME}")

    model = load_model()

    job_texts = [
        create_job_text(job)
        for job in jobs
    ]

    print("Creating job embeddings...")

    embeddings = model.encode(
        job_texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype="float32",
    )

    dimension = embeddings.shape[1]

    # Inner product on normalized vectors
    # is equivalent to cosine similarity.
    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(embeddings)

    faiss.write_index(
        index,
        str(INDEX_FILE),
    )

    metadata = []

    for job in jobs:
        metadata.append(
            {
                "job_id": job["id"],
                "title": job["title"],
                "company_name": job["company_name"],
                "location": job["location"],
                "source_url": job["source_url"],
            }
        )

    with METADATA_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("Combined semantic job index created.")
    print(f"Jobs indexed: {len(jobs)}")
    print(f"Embedding dimension: {dimension}")
    print(f"FAISS index: {INDEX_FILE}")
    print(f"Metadata: {METADATA_FILE}")


if __name__ == "__main__":
    main()
