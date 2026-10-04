import json
import sys
from pathlib import Path

# Add project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import faiss
import numpy as np

from backend.app.database import get_connection
from backend.app.hybrid_retrieval import load_model


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = PROJECT_ROOT / "data" / "indexes"
LIVE_INDEX_FILE = INDEX_DIR / "live_jobs.faiss"
LIVE_METADATA_FILE = INDEX_DIR / "live_jobs_metadata.json"

LIVE_SOURCE_TYPES = (
    "jobicy",
    "himalayas",
    "remoteok",
)


def get_live_jobs():
    """Get all active jobs from the supported live sources."""

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
                source_type,
                application_url
            FROM jobs
            WHERE source_type IN ({placeholders})
              AND is_active = 1
            ORDER BY id
            """,
            LIVE_SOURCE_TYPES,
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def create_job_text(job):
    """Create the same semantic text representation used by the main index."""

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


def _replace_file(temp_path, final_path):
    """Replace a generated file with the new version atomically where supported."""

    temp_path.replace(final_path)


def build_live_index():
    """
    Rebuild the semantic index for active live jobs only.

    This function is reusable from the live synchronization service and can
    also be executed from the command line through main().
    """

    INDEX_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    jobs = get_live_jobs()

    print(f"Active live jobs found: {len(jobs)}")

    live_counts = {
        source_type: 0
        for source_type in LIVE_SOURCE_TYPES
    }

    for job in jobs:
        source_type = job["source_type"]

        if source_type in live_counts:
            live_counts[source_type] += 1

    print("Active live jobs by source:")

    for source_type in LIVE_SOURCE_TYPES:
        print(
            f"  {source_type}: "
            f"{live_counts[source_type]}"
        )

    # Keep the live index absent when there are no active live jobs.
    if not jobs:
        if LIVE_INDEX_FILE.exists():
            LIVE_INDEX_FILE.unlink()

        if LIVE_METADATA_FILE.exists():
            LIVE_METADATA_FILE.unlink()

        return {
            "jobs_indexed": 0,
            "embedding_dimension": 0,
            "index_file": str(LIVE_INDEX_FILE),
            "metadata_file": str(LIVE_METADATA_FILE),
        }

    print()
    print(f"Loading model: {MODEL_NAME}")

    model = load_model()

    job_texts = [
        create_job_text(job)
        for job in jobs
    ]

    print("Creating live job embeddings...")

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

    # Inner product on normalized vectors is cosine similarity.
    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(embeddings)

    metadata = []

    for job in jobs:
        metadata.append(
            {
                "job_id": job["id"],
                "title": job["title"],
                "company_name": job["company_name"],
                "location": job["location"],
                "source_url": job["source_url"],
                "source_type": job["source_type"],
                "application_url": job["application_url"],
            }
        )

    temp_index = LIVE_INDEX_FILE.with_name(
        LIVE_INDEX_FILE.name + ".tmp"
    )
    temp_metadata = LIVE_METADATA_FILE.with_name(
        LIVE_METADATA_FILE.name + ".tmp"
    )

    try:
        faiss.write_index(
            index,
            str(temp_index),
        )

        with temp_metadata.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                metadata,
                file,
                ensure_ascii=False,
                indent=2,
            )

        _replace_file(
            temp_index,
            LIVE_INDEX_FILE,
        )
        _replace_file(
            temp_metadata,
            LIVE_METADATA_FILE,
        )

    finally:
        # Clean up a partially written temporary file if an error occurs.
        if temp_index.exists():
            temp_index.unlink()

        if temp_metadata.exists():
            temp_metadata.unlink()

    print()
    print("Live semantic job index created.")
    print(f"Jobs indexed: {len(jobs)}")
    print(f"Embedding dimension: {dimension}")
    print(f"FAISS index: {LIVE_INDEX_FILE}")
    print(f"Metadata: {LIVE_METADATA_FILE}")

    return {
        "jobs_indexed": len(jobs),
        "embedding_dimension": dimension,
        "index_file": str(LIVE_INDEX_FILE),
        "metadata_file": str(LIVE_METADATA_FILE),
    }


def main():
    build_live_index()


if __name__ == "__main__":
    main()
