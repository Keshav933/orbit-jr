import csv
import re
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.database import get_connection


ESCO_FILE = Path("data/raw/esco/skills_en.csv")


def normalize_text(text):
    if not text:
        return ""

    text = str(text).strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


def split_aliases(text):
    if not text:
        return []

    text = str(text).strip()

    parts = re.split(r"[|\n]", text)

    aliases = []

    for part in parts:
        part = part.strip()

        if part:
            aliases.append(part)

    return aliases


def insert_skill(cursor, name, category, esco_uri):
    query = """
        INSERT INTO skills (name, category, esco_uri)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id),
            category = VALUES(category),
            esco_uri = VALUES(esco_uri)
    """

    cursor.execute(
        query,
        (
            name[:150],
            category[:100] if category else None,
            esco_uri[:500] if esco_uri else None,
        ),
    )

    return cursor.lastrowid


def insert_alias(cursor, skill_id, alias):
    normalized_alias = normalize_text(alias)

    if not normalized_alias:
        return

    query = """
        INSERT IGNORE INTO skill_aliases
        (skill_id, alias, normalized_alias, source)
        VALUES (%s, %s, %s, 'esco')
    """

    cursor.execute(
        query,
        (
            skill_id,
            alias[:255],
            normalized_alias[:255],
        ),
    )


def main():
    if not ESCO_FILE.exists():
        print(f"ESCO file not found: {ESCO_FILE}")
        return

    connection = get_connection()
    cursor = connection.cursor()

    skill_count = 0
    alias_count = 0

    try:
        with ESCO_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:
                preferred_label = (
                    row.get("preferredLabel") or ""
                ).strip()

                if not preferred_label:
                    continue

                skill_type = (
                    row.get("skillType") or ""
                ).strip()

                concept_uri = (
                    row.get("conceptUri") or ""
                ).strip()

                skill_id = insert_skill(
                    cursor,
                    preferred_label,
                    skill_type,
                    concept_uri,
                )

                skill_count += 1

                insert_alias(
                    cursor,
                    skill_id,
                    preferred_label,
                )
                alias_count += 1

                alternatives = split_aliases(
                    row.get("altLabels")
                )

                for alias in alternatives:
                    insert_alias(
                        cursor,
                        skill_id,
                        alias,
                    )
                    alias_count += 1

        connection.commit()

        print("ESCO import completed.")
        print(f"Processed ESCO records: {skill_count}")
        print(f"Alias records processed: {alias_count}")

    except Exception as error:
        connection.rollback()
        print("ESCO import failed.")
        print(error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()