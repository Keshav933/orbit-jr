import re
from pathlib import Path
from backend.app.database import get_connection
from backend.app.resume_parser import extract_resume_text
from backend.app.skill_extractor import extract_skills_from_text
from backend.app.recommendations import get_recommendations
UPLOAD_DIR = Path("backend/uploads")
def clean_filename(filename):
    """
    Keep only the filename and remove unsafe path parts.
    """
    filename = Path(filename or "resume.pdf").name
    filename = re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        filename,
    )
    return filename
def get_or_create_user(
    cursor,
    full_name,
    email,
):
    """
    Create a user if the email does not exist.
    If the email already exists, return the
    existing user's ID.
    """
    cursor.execute(
        """
        INSERT INTO users
        (
            full_name,
            email
        )
        VALUES
        (
            %s,
            %s
        )
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id),
            full_name = VALUES(full_name)
        """,
        (
            full_name,
            email,
        ),
    )
    return cursor.lastrowid
def get_or_create_profile(
    cursor,
    user_id,
    education,
    experience_years,
    location,
    preferred_role,
    summary,
):
    """
    Create the candidate profile if it does not exist.
    Otherwise update the existing profile.
    """
    cursor.execute(
        """
        SELECT id
        FROM profiles
        WHERE user_id = %s
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if row:
        profile_id = row[0]
        cursor.execute(
            """
            UPDATE profiles
            SET
                education = %s,
                experience_years = %s,
                location = %s,
                preferred_role = %s,
                summary = %s
            WHERE id = %s
            """,
            (
                education,
                experience_years,
                location,
                preferred_role,
                summary,
                profile_id,
            ),
        )
        return profile_id
    cursor.execute(
        """
        INSERT INTO profiles
        (
            user_id,
            education,
            experience_years,
            location,
            preferred_role,
            summary
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            user_id,
            education,
            experience_years,
            location,
            preferred_role,
            summary,
        ),
    )
    return cursor.lastrowid
def process_resume(
    cursor,
    user_id,
    profile_id,
    filename,
    file_bytes,
):
    """
    Save the resume, extract text and detect skills.
    """
    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    safe_filename = clean_filename(
        filename
    )
    resume_path = (
        UPLOAD_DIR / safe_filename
    )
    resume_path.write_bytes(
        file_bytes
    )
    # Extract resume text.
    extracted_text = extract_resume_text(
        resume_path
    )
    if not extracted_text:
        raise ValueError(
            "Could not extract text from the resume PDF."
        )
    # Mark previous resumes as inactive.
    cursor.execute(
        """
        UPDATE resumes
        SET is_active = FALSE
        WHERE user_id = %s
        """,
        (user_id,),
    )
    # Store new resume.
    cursor.execute(
        """
        INSERT INTO resumes
        (
            user_id,
            file_name,
            file_path,
            extracted_text,
            is_active
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            TRUE
        )
        """,
        (
            user_id,
            safe_filename,
            str(resume_path),
            extracted_text,
        ),
    )
    resume_id = cursor.lastrowid
    # Extract candidate skills.
    detected_skills = (
        extract_skills_from_text(
            extracted_text
        )
    )
    # Rebuild resume-derived skills.
    cursor.execute(
        """
        DELETE FROM profile_skills
        WHERE profile_id = %s
          AND source = 'resume'
        """,
        (profile_id,),
    )
    for skill in detected_skills:
        cursor.execute(
            """
            INSERT INTO profile_skills
            (
                profile_id,
                skill_id,
                skill_level,
                source
            )
            VALUES
            (
                %s,
                %s,
                NULL,
                'resume'
            )
            ON DUPLICATE KEY UPDATE
                source = 'resume'
            """,
            (
                profile_id,
                skill["skill_id"],
            ),
        )
    return {
        "resume_id": resume_id,
        "file_name": safe_filename,
        "skill_count": len(
            detected_skills
        ),
        "skills": detected_skills,
    }
def onboard_candidate(
    full_name,
    email,
    education,
    experience_years,
    location,
    preferred_role,
    summary,
    filename,
    file_bytes,
    top_k=10,
):
    """
    Complete candidate onboarding:
        user
        profile
        resume
        skill extraction
        recommendations
    """
    connection = get_connection()
    # Normal cursor is used because we need
    # lastrowid and simple SQL results.
    cursor = connection.cursor()
    try:
        user_id = get_or_create_user(
            cursor,
            full_name,
            email,
        )
        profile_id = get_or_create_profile(
            cursor,
            user_id,
            education,
            experience_years,
            location,
            preferred_role,
            summary,
        )
        resume_info = process_resume(
            cursor,
            user_id,
            profile_id,
            filename,
            file_bytes,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    # Generate the first recommendation page only after the
    # database transaction has been committed.
    recommendation_page_size = min(
        max(1, int(top_k or 10)),
        20,
    )
    recommendation_result = get_recommendations(
        profile_id,
        top_k=recommendation_page_size,
        page=1,
        page_size=recommendation_page_size,
    )
    return {
        "message": "Candidate onboarding completed",
        "user_id": user_id,
        "profile_id": profile_id,
        "resume": resume_info,
        "recommendation_count": recommendation_result[
            "total_count"
        ],
        "recommendations": recommendation_result[
            "items"
        ],
    }