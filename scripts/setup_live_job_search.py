# """
# Create the database fields required by
# ORBIT-JR live job research.
# """

# from __future__ import annotations

# import sys
# from pathlib import Path


# PROJECT_ROOT = Path(
#     __file__
# ).resolve().parents[1]

# sys.path.insert(
#     0,
#     str(PROJECT_ROOT),
# )


# from backend.app.database import (  # noqa: E402
#     get_connection,
# )


# COLUMN_DEFINITIONS = {

#     (
#         "profiles",
#         "graduation_year",
#     ): "INT NULL",

#     (
#         "jobs",
#         "application_url",
#     ): "VARCHAR(1000) NULL",

#     (
#         "jobs",
#         "canonical_key",
#     ): "VARCHAR(64) NULL",

#     (
#         "jobs",
#         "verification_status",
#     ): "VARCHAR(40) NULL",

#     (
#         "jobs",
#         "agent_agreement",
#     ): "DECIMAL(5,4) NULL",

#     (
#         "jobs",
#         "verification_sources",
#     ): "JSON NULL",

#     (
#         "jobs",
#         "research_query",
#     ): "TEXT NULL",

#     (
#         "jobs",
#         "verified_at",
#     ): "DATETIME NULL",
# }


# def column_exists(
#     cursor,
#     table: str,
#     column: str,
# ) -> bool:

#     cursor.execute(
#         """
#         SELECT COUNT(*)
#         FROM information_schema.COLUMNS
#         WHERE TABLE_SCHEMA = DATABASE()
#         AND TABLE_NAME = %s
#         AND COLUMN_NAME = %s
#         """,
#         (
#             table,
#             column,
#         ),
#     )

#     return int(
#         cursor.fetchone()[0]
#     ) > 0


# def index_exists(
#     cursor,
#     table: str,
#     index_name: str,
# ) -> bool:

#     cursor.execute(
#         """
#         SELECT COUNT(*)
#         FROM information_schema.STATISTICS
#         WHERE TABLE_SCHEMA = DATABASE()
#         AND TABLE_NAME = %s
#         AND INDEX_NAME = %s
#         """,
#         (
#             table,
#             index_name,
#         ),
#     )

#     return int(
#         cursor.fetchone()[0]
#     ) > 0


# def main() -> None:

#     connection = get_connection()

#     cursor = connection.cursor()

#     try:

#         for (
#             table,
#             column,
#         ), definition in (
#             COLUMN_DEFINITIONS.items()
#         ):

#             if column_exists(
#                 cursor,
#                 table,
#                 column,
#             ):

#                 print(
#                     f"Already exists: "
#                     f"{table}.{column}"
#                 )

#                 continue

#             cursor.execute(
#                 f"""
#                 ALTER TABLE {table}
#                 ADD COLUMN {column}
#                 {definition}
#                 """
#             )

#             print(
#                 f"Added: "
#                 f"{table}.{column}"
#             )

#         if not index_exists(
#             cursor,
#             "jobs",
#             "uq_jobs_canonical_key",
#         ):

#             cursor.execute(
#                 """
#                 ALTER TABLE jobs
#                 ADD UNIQUE INDEX
#                 uq_jobs_canonical_key
#                 (canonical_key)
#                 """
#             )

#             print(
#                 "Added: "
#                 "jobs.uq_jobs_canonical_key"
#             )

#         else:

#             print(
#                 "Already exists: "
#                 "jobs.uq_jobs_canonical_key"
#             )

#         connection.commit()

#         print(
#             "Live job research migration "
#             "completed successfully."
#         )

#     except Exception:

#         connection.rollback()
#         raise

#     finally:

#         cursor.close()
#         connection.close()


# if __name__ == "__main__":
#     main()