from backend.app.database import get_connection


def get_user_id_from_profile(profile_id):
    """
    Convert profile ID into its related user ID.
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT user_id
            FROM profiles
            WHERE id = %s
            """,
            (profile_id,),
        )

        row = cursor.fetchone()

        if not row:
            return None

        return row[0]

    finally:
        cursor.close()
        connection.close()


def get_saved_job_ids(profile_id):
    """
    Get job IDs saved by this candidate.
    """

    user_id = get_user_id_from_profile(
        profile_id
    )

    if not user_id:
        return []

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT job_id
            FROM saved_jobs
            WHERE user_id = %s
              AND status = 'saved'
            ORDER BY created_at DESC
            """,
            (user_id,),
        )

        return [
            row[0]
            for row in cursor.fetchall()
        ]

    finally:
        cursor.close()
        connection.close()


def save_job(profile_id, job_id):
    """
    Save a job for the candidate.
    """

    user_id = get_user_id_from_profile(
        profile_id
    )

    if not user_id:
        return None

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Make sure the job exists.
        cursor.execute(
            """
            SELECT id
            FROM jobs
            WHERE id = %s
            """,
            (job_id,),
        )

        if not cursor.fetchone():
            return False

        cursor.execute(
            """
            INSERT INTO saved_jobs
            (
                user_id,
                job_id,
                status
            )
            VALUES
            (
                %s,
                %s,
                'saved'
            )
            ON DUPLICATE KEY UPDATE
                status = 'saved'
            """,
            (
                user_id,
                job_id,
            ),
        )

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def remove_saved_job(
    profile_id,
    job_id,
):
    """
    Remove a saved job.
    """

    user_id = get_user_id_from_profile(
        profile_id
    )

    if not user_id:
        return False

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM saved_jobs
            WHERE user_id = %s
              AND job_id = %s
            """,
            (
                user_id,
                job_id,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def get_saved_jobs(profile_id):
    """
    Return complete information for saved jobs.
    """

    user_id = get_user_id_from_profile(
        profile_id
    )

    if not user_id:
        return []

    connection = get_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    try:
        cursor.execute(
            """
            SELECT
                sj.job_id,
                sj.status,
                sj.created_at,

                j.title,
                j.company_name,
                j.location,
                j.is_remote,
                j.posted_date,
                j.source_url

            FROM saved_jobs sj

            JOIN jobs j
                ON j.id = sj.job_id

            WHERE sj.user_id = %s

            ORDER BY sj.created_at DESC
            """,
            (user_id,),
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()