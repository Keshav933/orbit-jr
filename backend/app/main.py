import shutil
import uuid
import os
from pathlib import Path
import mysql.connector
from mysql.connector import IntegrityError
from fastapi.middleware.cors import CORSMiddleware
from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Form,
    UploadFile,
    File,
)
from backend.app.database import get_connection
from backend.app.live_job_research import (
    router as live_job_research_router,
)
from backend.app.schemas import (
    UserCreate,
    UserUpdate,
)
from backend.app.resume_parser import (
    extract_resume_text,
)
from backend.app.skill_extractor import (
    extract_skills_from_text,
)
from backend.app.recommendations import (
    get_recommendations,
)
from backend.app.job_details import (
    get_job_details,
)
from backend.app.saved_jobs import (
    get_saved_job_ids,
    save_job,
    remove_saved_job,
    get_saved_jobs,
)
from backend.app.onboarding import (
    onboard_candidate,
)
app = FastAPI(title="ORBIT-JR API")

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,https://orbit-jr-frontend.onrender.com",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    live_job_research_router
)
@app.get("/")
def home():
    return {
        "message": "ORBIT-JR API is running"
    }
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok"
    }
@app.get("/api/v1/database-test")
def database_test():
    connection = None
    try:
        connection = get_connection()
        if connection.is_connected():
            return {
                "status": "ok",
                "message": "MySQL connection successful"
            }
        return {
            "status": "error",
            "message": "MySQL connection failed"
        }
    except mysql.connector.Error:
        raise HTTPException(
            status_code=500,
            detail="Could not connect to database"
        )
    finally:
        if connection is not None and connection.is_connected():
            connection.close()
@app.post("/api/v1/users")
def create_user(user: UserCreate):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        query = """
            INSERT INTO users (full_name, email)
            VALUES (%s, %s)
        """
        values = (
            user.full_name,
            user.email
        )
        cursor.execute(query, values)
        connection.commit()
        user_id = cursor.lastrowid
        return {
            "message": "User created successfully",
            "user_id": user_id
        }
    except IntegrityError:
        if connection is not None:
            connection.rollback()
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
@app.get("/api/v1/users")
def get_users():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        query = """
            SELECT id, full_name, email, created_at
            FROM users
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "full_name": row[1],
                "email": row[2],
                "created_at": row[3]
            })
        return {
            "users": users
        }
    except mysql.connector.Error:
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
@app.get("/api/v1/users/{user_id}")
def get_user(user_id: int):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        query = """
            SELECT id, full_name, email, created_at
            FROM users
            WHERE id = %s
        """
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        return {
            "id": row[0],
            "full_name": row[1],
            "email": row[2],
            "created_at": row[3]
        }
    except HTTPException:
        raise
    except mysql.connector.Error:
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
@app.put("/api/v1/users/{user_id}")
def update_user(user_id: int, user: UserUpdate):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        check_query = """
            SELECT id
            FROM users
            WHERE id = %s
        """
        cursor.execute(check_query, (user_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        update_query = """
            UPDATE users
            SET full_name = %s,
                email = %s
            WHERE id = %s
        """
        values = (
            user.full_name,
            user.email,
            user_id
        )
        cursor.execute(update_query, values)
        connection.commit()
        return {
            "message": "User updated successfully"
        }
    except HTTPException:
        raise
    except IntegrityError:
        if connection is not None:
            connection.rollback()
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
@app.delete("/api/v1/users/{user_id}")
def delete_user(user_id: int):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        check_query = """
            SELECT id
            FROM users
            WHERE id = %s
        """
        cursor.execute(check_query, (user_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        delete_query = """
            DELETE FROM users
            WHERE id = %s
        """
        cursor.execute(delete_query, (user_id,))
        connection.commit()
        return {
            "message": "User deleted successfully"
        }
    except HTTPException:
        raise
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
@app.post("/api/v1/resumes/upload/{user_id}")
def upload_resume(
    user_id: int,
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select a file"
        )
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )
    connection = None
    cursor = None
    saved_file = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        check_query = """
            SELECT id
            FROM users
            WHERE id = %s
        """
        cursor.execute(check_query, (user_id,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        upload_folder = Path("uploads")
        upload_folder.mkdir(exist_ok=True)
        new_file_name = (
            f"{uuid.uuid4().hex}.pdf"
        )
        saved_file = upload_folder / new_file_name
        with open(saved_file, "wb") as output_file:
            shutil.copyfileobj(
                file.file,
                output_file
            )
        extracted_text = extract_resume_text(
            saved_file
        )
        if not extracted_text:
            saved_file.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from this PDF"
            )
        query = """
            INSERT INTO resumes (
                user_id,
                file_name,
                file_path,
                extracted_text,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            user_id,
            file.filename,
            str(saved_file),
            extracted_text,
            True
        )
        cursor.execute(query, values)
        connection.commit()
        resume_id = cursor.lastrowid
        return {
            "message": "Resume uploaded successfully",
            "resume_id": resume_id,
            "file_name": file.filename,
            "text_length": len(extracted_text)
        }
    except HTTPException:
        if connection is not None:
            connection.rollback()
        raise
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        if saved_file is not None:
            saved_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )
    except Exception:
        if connection is not None:
            connection.rollback()
        if saved_file is not None:
            saved_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Could not process the PDF"
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
@app.post("/api/v1/resumes/{resume_id}/extract-skills")
def extract_resume_skills(resume_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        # Get resume text and user
        cursor.execute(
            """
            SELECT user_id, extracted_text
            FROM resumes
            WHERE id = %s
            """,
            (resume_id,),
        )
        resume = cursor.fetchone()
        if not resume:
            raise HTTPException(
                status_code=404,
                detail="Resume not found",
            )
        if not resume["extracted_text"]:
            raise HTTPException(
                status_code=400,
                detail="Resume does not contain extracted text",
            )
        # Find the user's profile
        cursor.execute(
            """
            SELECT id
            FROM profiles
            WHERE user_id = %s
            """,
            (resume["user_id"],),
        )
        profile = cursor.fetchone()
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Profile not found for this user",
            )
        profile_id = profile["id"]
        # Extract skills
        detected_skills = extract_skills_from_text(
            resume["extracted_text"]
        )
        # Remove previously extracted resume skills.
        cursor.execute(
            """
            DELETE FROM profile_skills
            WHERE profile_id = %s
              AND source = 'resume'
            """,
            (profile_id,),
        )
        # Insert new skills
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
                VALUES (%s, %s, %s, 'resume')
                ON DUPLICATE KEY UPDATE
                    source = 'resume'
                """,
                (
                    profile_id,
                    skill["skill_id"],
                    None,
                ),
            )
        connection.commit()
        return {
            "message": "Resume skills extracted successfully",
            "resume_id": resume_id,
            "profile_id": profile_id,
            "skill_count": len(detected_skills),
            "skills": detected_skills,
        }
    except HTTPException:
        connection.rollback()
        raise
    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
    finally:
        cursor.close()
        connection.close()
@app.get("/api/v1/recommendations/{profile_id}")
def recommendations(
    profile_id: int,
    top_k: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str = Query(
        default="",
        max_length=100,
    ),
    location: str = Query(
        default="",
        max_length=100,
    ),
    role: str = Query(
        default="",
        max_length=100,
    ),
    remote_only: bool = Query(
        default=False,
    ),
    min_score: float = Query(
        default=0.0,
        ge=0.0,
        le=1.0,
    ),
    experience_level: str = Query(
        default="",
        max_length=30,
    ),
    employment_type: str = Query(
        default="",
        max_length=50,
    ),
    sort_by: str = Query(
        default="recent",
        max_length=30,
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=20,
    ),
):
    """
    Return personalized, filtered and sorted
    job recommendations.
    """
    results = get_recommendations(
        profile_id=profile_id,
        top_k=top_k,
        search=search,
        location=location,
        role=role,
        remote_only=remote_only,
        min_score=min_score,
        experience_level=experience_level,
        employment_type=employment_type,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return {
        "profile_id": profile_id,
        "count": results["total_count"],
        "page": results["page"],
        "page_size": results["page_size"],
        "total_pages": results["total_pages"],
        "has_more": results["has_more"],
        "filters": {
            "search": search,
            "location": location,
            "role": role,
            "remote_only": remote_only,
            "min_score": min_score,
            "experience_level": (
                experience_level
            ),
            "employment_type": (
                employment_type
            ),
            "sort_by": sort_by,
        },
        "recommendations": results["items"],
    }
@app.get("/api/v1/jobs/{job_id}")
def job_details(job_id: int):
    """
    Return complete information about one job.
    """
    job = get_job_details(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )
    return job
@app.get("/api/v1/saved-jobs/{profile_id}")
def saved_job_list(profile_id: int):
    """
    Return all jobs saved by the candidate.
    """
    jobs = get_saved_jobs(
        profile_id
    )
    return {
        "profile_id": profile_id,
        "count": len(jobs),
        "jobs": jobs,
    }
@app.get("/api/v1/saved-jobs/{profile_id}/ids")
def saved_job_ids(profile_id: int):
    """
    Return only saved job IDs.
    Useful for the recommendation dashboard.
    """
    job_ids = get_saved_job_ids(
        profile_id
    )
    return {
        "profile_id": profile_id,
        "job_ids": job_ids,
    }
@app.post("/api/v1/saved-jobs/{profile_id}/{job_id}")
def save_job_endpoint(
    profile_id: int,
    job_id: int,
):
    """
    Save one job for a candidate.
    """
    result = save_job(
        profile_id,
        job_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Profile not found",
        )
    if result is False:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )
    return {
        "message": "Job saved successfully",
        "profile_id": profile_id,
        "job_id": job_id,
    }
@app.delete("/api/v1/saved-jobs/{profile_id}/{job_id}")
def remove_saved_job_endpoint(
    profile_id: int,
    job_id: int,
):
    """
    Remove a saved job.
    """
    removed = remove_saved_job(
        profile_id,
        job_id,
    )
    return {
        "message": (
            "Job removed from saved jobs"
            if removed
            else "Job was not saved"
        ),
        "profile_id": profile_id,
        "job_id": job_id,
    }
@app.post("/api/v1/candidates/onboard")
async def candidate_onboarding(
    full_name: str = Form(...),
    email: str = Form(...),
    education: str = Form(""),
    experience_years: float = Form(0),
    location: str = Form(""),
    preferred_role: str = Form(""),
    summary: str = Form(""),
    resume: UploadFile = File(...),
):
    """
    Create/update candidate profile, process the resume,
    extract skills and return job recommendations.
    """
    filename = resume.filename or "resume.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF resumes are supported.",
        )
    file_bytes = await resume.read()
    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Resume file is empty.",
        )
    try:
        result = onboard_candidate(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            education=education.strip(),
            experience_years=experience_years,
            location=location.strip(),
            preferred_role=preferred_role.strip(),
            summary=summary.strip(),
            filename=filename,
            file_bytes=file_bytes,
            top_k=10,
        )
        return result
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )