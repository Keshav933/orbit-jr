import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.database import get_connection


def main():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'skill_aliases'
        """)

        columns = {
            row[0]
            for row in cursor.fetchall()
        }

        if "normalized_alias" not in columns:
            cursor.execute("""
                ALTER TABLE skill_aliases
                ADD COLUMN normalized_alias VARCHAR(255) NULL
                AFTER alias
            """)

            cursor.execute("""
                UPDATE skill_aliases
                SET normalized_alias = LOWER(TRIM(alias))
                WHERE normalized_alias IS NULL
            """)

            cursor.execute("""
                ALTER TABLE skill_aliases
                MODIFY COLUMN normalized_alias VARCHAR(255) NOT NULL
            """)

            print("Added normalized_alias column.")

        if "source" not in columns:
            cursor.execute("""
                ALTER TABLE skill_aliases
                ADD COLUMN source VARCHAR(50)
                DEFAULT 'esco'
                AFTER normalized_alias
            """)

            print("Added source column.")

        connection.commit()

        print("skill_aliases table is ready.")

    except Exception as error:
        connection.rollback()
        print("Schema update failed.")
        print(error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()