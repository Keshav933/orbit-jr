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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_jobs (
                id INT AUTO_INCREMENT PRIMARY KEY,

                user_id INT NOT NULL,

                job_id INT NOT NULL,

                status VARCHAR(30) NOT NULL DEFAULT 'saved',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (job_id)
                    REFERENCES jobs(id)
                    ON DELETE CASCADE,

                UNIQUE (user_id, job_id),

                INDEX idx_saved_jobs_user
                    (user_id),

                INDEX idx_saved_jobs_status
                    (status)
            )
            """
        )

        connection.commit()

        print("saved_jobs table is ready.")

    except Exception as error:
        connection.rollback()

        print("Could not create saved_jobs table.")
        print(error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()