"""

ORBIT-JR free live job source ingestion.



This replaces the earlier LLM-based live_job_research.py.

No OpenAI or Gemini API is required.



Supported public sources in this first version:

- Greenhouse public job boards

- Lever public postings

- Ashby public job board API

- Jobicy public remote-jobs API

- Himalayas public remote-jobs API

- Remote OK public JSON feed



The module keeps the existing ORBIT-JR live-job endpoint:

    POST /api/v1/live-jobs/search/{profile_id}



It discovers current public listings, normalizes them and returns them.

Database persistence and frontend integration are added in later steps.

"""



from __future__ import annotations



import html

import json

import re

from concurrent.futures import ThreadPoolExecutor, as_completed

from datetime import date, datetime, timedelta

from pathlib import Path

from typing import Any



import requests

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel



from backend.app.database import get_connection





router = APIRouter(

    prefix="/api/v1/live-jobs",

    tags=["live-jobs"],

)





PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_FILE = PROJECT_ROOT / "data" / "live_job_sources.json"



REQUEST_TIMEOUT = 20

DEFAULT_DAYS = 30

MAX_JOBS_PER_SOURCE = 100





class LiveJob(BaseModel):

    title: str = ""

    company_name: str = ""

    location: str = ""

    is_remote: bool = False

    employment_type: str = ""

    seniority_level: str = ""

    job_function: str = ""

    industry: str = ""

    description: str = ""

    experience_min: float | None = None

    experience_max: float | None = None

    posted_date: str | None = None

    source_name: str = ""

    source_url: str = ""

    application_url: str = ""

    external_id: str = ""

    source_type: str = ""





class ProfileContext(BaseModel):

    profile_id: int

    full_name: str = ""

    education: str = ""

    experience_years: float = 0

    location: str = ""

    preferred_role: str = ""

    summary: str = ""

    skills: list[str] = []





def clean_text(value: Any) -> str:

    if value is None:

        return ""



    text = html.unescape(str(value))

    text = re.sub(r"<[^>]+>", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()





def normalize_text(value: Any) -> str:

    text = clean_text(value).lower()

    text = re.sub(r"[^a-z0-9+#. ]+", " ", text)

    return re.sub(r"\s+", " ", text).strip()





def normalize_url(value: Any) -> str:

    value = str(value or "").strip()



    if not value:

        return ""



    # Remove tracking parameters while keeping the actual URL.

    value = re.sub(r"[?&](utm_[^=&]+|gclid|fbclid)=[^&]*", "", value)

    value = value.rstrip(" ?&")



    return value





def parse_date(value: Any) -> str | None:

    if value is None:

        return None



    text = str(value).strip()



    if not text:

        return None



    # ISO timestamps such as 2026-10-01T12:30:00Z

    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)

    if match:

        return match.group(1)



    # Unix seconds / milliseconds.

    if text.isdigit():

        try:

            number = int(text)

            if number > 10_000_000_000:

                number //= 1000

            return datetime.fromtimestamp(number).date().isoformat()

        except (ValueError, OverflowError, OSError):

            return None



    return None





def is_recent(posted_date: str | None, days: int = DEFAULT_DAYS) -> bool:

    if not posted_date:

        return True



    try:

        posted = date.fromisoformat(posted_date)

    except ValueError:

        return True



    return posted >= date.today() - timedelta(days=days)





def normalize_employment_type(value: Any) -> str:

    text = normalize_text(value)



    if "intern" in text:

        return "Internship"

    if "full time" in text or "full-time" in text:

        return "Full-time"

    if "part time" in text or "part-time" in text:

        return "Part-time"

    if "contract" in text:

        return "Contract"

    if "temporary" in text:

        return "Temporary"



    return clean_text(value)





def infer_remote(location: str, raw_text: str = "") -> bool:

    text = normalize_text(f"{location} {raw_text}")

    return any(

        phrase in text

        for phrase in (

            "remote",

            "work from home",

            "distributed",

            "anywhere",

        )

    )





def job_key(job: LiveJob) -> str:

    """Stable cross-source key used for first-pass deduplication."""



    from hashlib import sha256



    company = normalize_text(job.company_name)

    title = normalize_text(job.title)

    location = normalize_text(job.location)

    url = normalize_url(job.source_url)



    if url:

        identity = f"url|{url}"

    else:

        identity = f"text|{company}|{title}|{location}"



    return sha256(identity.encode("utf-8")).hexdigest()





def load_sources() -> list[dict[str, Any]]:

    if not SOURCE_FILE.exists():

        return []



    with SOURCE_FILE.open("r", encoding="utf-8") as file:

        data = json.load(file)



    if not isinstance(data, list):

        raise ValueError(

            "data/live_job_sources.json must contain a list."

        )



    return [

        item

        for item in data

        if isinstance(item, dict)

        and item.get("enabled", True)

    ]





def get_profile_context(profile_id: int) -> ProfileContext:

    connection = get_connection()

    cursor = connection.cursor(dictionary=True)



    try:

        cursor.execute(

            """

            SELECT

                p.id AS profile_id,

                COALESCE(u.full_name, '') AS full_name,

                COALESCE(p.education, '') AS education,

                COALESCE(p.experience_years, 0) AS experience_years,

                COALESCE(p.location, '') AS location,

                COALESCE(p.preferred_role, '') AS preferred_role,

                COALESCE(p.summary, '') AS summary

            FROM profiles p

            JOIN users u ON u.id = p.user_id

            WHERE p.id = %s

            LIMIT 1

            """,

            (profile_id,),

        )



        row = cursor.fetchone()



        if not row:

            raise ValueError(f"Profile {profile_id} was not found.")



        cursor.execute(

            """

            SELECT DISTINCT s.name

            FROM profile_skills ps

            JOIN skills s ON s.id = ps.skill_id

            WHERE ps.profile_id = %s

            ORDER BY s.name

            """,

            (profile_id,),

        )



        skills = [

            item["name"]

            for item in cursor.fetchall()

        ]



        return ProfileContext(

            profile_id=int(row["profile_id"]),

            full_name=str(row["full_name"] or ""),

            education=str(row["education"] or ""),

            experience_years=float(row["experience_years"] or 0),

            location=str(row["location"] or ""),

            preferred_role=str(row["preferred_role"] or ""),

            summary=str(row["summary"] or ""),

            skills=skills,

        )



    finally:

        cursor.close()

        connection.close()





def build_profile_query(profile: ProfileContext) -> str:

    parts: list[str] = []



    if profile.preferred_role:

        parts.append(profile.preferred_role)



    if profile.education:

        parts.append(profile.education)



    parts.extend(profile.skills[:12])



    if profile.location:

        parts.append(profile.location)



    return " ".join(parts).strip()





def matches_profile(job: LiveJob, profile: ProfileContext) -> bool:

    """

    Lightweight pre-filter only.



    The existing ORBIT-JR ranking engine remains the authoritative

    recommendation stage. This function only removes obviously unrelated

    live listings before they enter the database.

    """



    job_text = normalize_text(

        f"{job.title} {job.company_name} {job.location} {job.description}"

    )



    role = normalize_text(profile.preferred_role)

    if role:

        role_terms = [

            term

            for term in role.split()

            if len(term) >= 3

        ]



        if role_terms and any(term in job_text for term in role_terms):

            return True



    skill_hits = 0

    for skill in profile.skills:

        skill_normalized = normalize_text(skill)

        if skill_normalized and skill_normalized in job_text:

            skill_hits += 1



    if skill_hits >= 1:

        return True



    if profile.location:

        location = normalize_text(profile.location)

        if location and location in job_text:

            return True



    # Remote jobs can still be relevant when the profile has no location.

    return job.is_remote and not profile.location





def fetch_json(

    url: str,

    params: dict[str, Any] | None = None,

    headers: dict[str, str] | None = None,

) -> Any:

    response = requests.get(

        url,

        params=params,

        headers=headers,

        timeout=REQUEST_TIMEOUT,

    )

    response.raise_for_status()

    return response.json()





def fetch_greenhouse(source: dict[str, Any]) -> list[LiveJob]:

    slug = str(source.get("slug", "")).strip()

    if not slug:

        return []



    data = fetch_json(

        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",

        params={"content": "true"},

    )



    company = clean_text(source.get("company") or slug)

    jobs: list[LiveJob] = []



    for item in data.get("jobs", [])[:MAX_JOBS_PER_SOURCE]:

        location = clean_text(

            (item.get("location") or {}).get("name")

        )



        posted = parse_date(

            item.get("first_published")

            or item.get("updated_at")

        )



        jobs.append(

            LiveJob(

                title=clean_text(item.get("title")),

                company_name=company,

                location=location,

                is_remote=infer_remote(location, item.get("content", "")),

                employment_type="",

                seniority_level="",

                job_function=clean_text(

                    (item.get("departments") or [{}])[0].get("name")

                    if item.get("departments")

                    else ""

                ),

                industry="",

                description=clean_text(item.get("content")),

                posted_date=posted,

                source_name=company,

                source_url=normalize_url(item.get("absolute_url")),

                application_url=normalize_url(item.get("absolute_url")),

                external_id=str(item.get("id") or ""),

                source_type="greenhouse",

            )

        )



    return jobs





def fetch_lever(source: dict[str, Any]) -> list[LiveJob]:

    slug = str(source.get("slug", "")).strip()

    if not slug:

        return []



    data = fetch_json(

        f"https://api.lever.co/v0/postings/{slug}",

        params={"mode": "json"},

    )



    company = clean_text(source.get("company") or slug)

    jobs: list[LiveJob] = []



    for item in data[:MAX_JOBS_PER_SOURCE]:

        categories = item.get("categories") or {}



        location = clean_text(

            categories.get("location")

        )



        description = clean_text(

            item.get("description")

            or item.get("descriptionPlain")

        )



        jobs.append(

            LiveJob(

                title=clean_text(item.get("text")),

                company_name=company,

                location=location,

                is_remote=(

                    str(item.get("workplaceType", "")).lower()

                    == "remote"

                    or infer_remote(location, description)

                ),

                employment_type=normalize_employment_type(

                    categories.get("commitment")

                ),

                seniority_level="",

                job_function=clean_text(

                    categories.get("team")

                ),

                industry="",

                description=description,

                posted_date=parse_date(

                    item.get("createdAt")

                    or item.get("updatedAt")

                ),

                source_name=company,

                source_url=normalize_url(item.get("hostedUrl")),

                application_url=normalize_url(

                    item.get("applyUrl")

                    or item.get("hostedUrl")

                ),

                external_id=str(item.get("id") or ""),

                source_type="lever",

            )

        )



    return jobs





def fetch_ashby(source: dict[str, Any]) -> list[LiveJob]:

    slug = str(source.get("slug", "")).strip()

    if not slug:

        return []



    data = fetch_json(

        f"https://api.ashbyhq.com/posting-api/job-board/{slug}"

    )



    company = clean_text(source.get("company") or slug)

    jobs: list[LiveJob] = []



    for item in data.get("jobs", [])[:MAX_JOBS_PER_SOURCE]:

        if item.get("isListed") is False:

            continue



        location = clean_text(item.get("location"))

        description = clean_text(

            item.get("descriptionPlain")

            or item.get("descriptionHtml")

            or item.get("description")

        )



        jobs.append(

            LiveJob(

                title=clean_text(item.get("title")),

                company_name=company,

                location=location,

                is_remote=bool(item.get("isRemote")) or infer_remote(location, description),

                employment_type=normalize_employment_type(

                    item.get("employmentType")

                ),

                seniority_level=clean_text(item.get("jobLevel")),

                job_function=clean_text(item.get("department")),

                industry="",

                description=description,

                posted_date=parse_date(

                    item.get("publishedAt")

                    or item.get("updatedAt")

                ),

                source_name=company,

                source_url=normalize_url(item.get("jobUrl")),

                application_url=normalize_url(item.get("applyUrl")),

                external_id=str(item.get("id") or ""),

                source_type="ashby",

            )

        )



    return jobs



def fetch_jobicy(

    profile: ProfileContext,

) -> list[LiveJob]:



    params: dict[str, Any] = {

        "count": min(

            MAX_JOBS_PER_SOURCE,

            200,

        ),

    }



    # -----------------------------------------------------

    # We intentionally do not send the user's city/country

    # as Jobicy's "geo" parameter.

    #

    # Jobicy expects supported location slugs such as

    # "usa", "europe", and "apac".

    #

    # For ORBIT-JR, we fetch the public remote-job feed

    # and let our own matching pipeline decide relevance.

    # -----------------------------------------------------



    data = fetch_json(

        "https://jobicy.com/api/v2/remote-jobs",

        params=params,

    )



    # -----------------------------------------------------

    # Safety check

    # -----------------------------------------------------



    if not isinstance(

        data,

        dict,

    ):

        return []



    raw_jobs = (

        data.get("jobs")

        or []

    )



    if not isinstance(

        raw_jobs,

        list,

    ):

        return []



    jobs: list[LiveJob] = []



    # -----------------------------------------------------

    # Convert Jobicy records into ORBIT-JR LiveJob objects

    # -----------------------------------------------------



    for item in raw_jobs[

        :MAX_JOBS_PER_SOURCE

    ]:



        if not isinstance(

            item,

            dict,

        ):

            continue



        title = clean_text(

            item.get(

                "jobTitle"

            )

        )



        company_name = clean_text(

            item.get(

                "companyName"

            )

        )



        source_url = normalize_url(

            item.get(

                "url"

            )

        )



        # Skip incomplete records.

        if (

            not title

            or not company_name

            or not source_url

        ):

            continue



        # -------------------------------------------------

        # Location

        # -------------------------------------------------



        location = clean_text(

            item.get(

                "jobGeo"

            )

        )



        if not location:

            location = "Remote"



        # -------------------------------------------------

        # Job description

        # -------------------------------------------------



        description = clean_text(

            item.get(

                "jobDescription"

            )

            or item.get(

                "jobExcerpt"

            )

        )



        # -------------------------------------------------

        # Job type

        # -------------------------------------------------



        job_type_value = (

            item.get(

                "jobType"

            )

            or []

        )



        if isinstance(

            job_type_value,

            list,

        ):



            job_type_text = ", ".join(

                clean_text(value)

                for value in job_type_value

                if clean_text(value)

            )



        else:



            job_type_text = clean_text(

                job_type_value

            )



        employment_type = (

            normalize_employment_type(

                job_type_text

            )

        )



        # -------------------------------------------------

        # Industry / category

        # -------------------------------------------------



        industry_value = (

            item.get(

                "jobIndustry"

            )

            or []

        )



        if isinstance(

            industry_value,

            list,

        ):



            industry = ", ".join(

                clean_text(value)

                for value in industry_value

                if clean_text(value)

            )



        else:



            industry = clean_text(

                industry_value

            )



        # -------------------------------------------------

        # Seniority

        # -------------------------------------------------



        seniority_level = clean_text(

            item.get(

                "jobLevel"

            )

        )



        # -------------------------------------------------

        # Remote flag

        # -------------------------------------------------



        is_remote = infer_remote(

            location,

            description,

        )



        # Jobicy's endpoint itself is a remote-jobs feed,

        # so an empty/remote-style location is treated as

        # remote as well.

        if (

            not location

            or location.lower()

            in {

                "remote",

                "anywhere",

                "worldwide",

            }

        ):



            is_remote = True



        # -------------------------------------------------

        # Posted date

        # -------------------------------------------------



        posted_date = parse_date(

            item.get(

                "pubDate"

            )

        )



        # -------------------------------------------------

        # Jobicy record ID

        # -------------------------------------------------



        external_id = str(

            item.get(

                "id"

            )

            or ""

        )



        # -------------------------------------------------

        # Create ORBIT-JR job object

        # -------------------------------------------------



        jobs.append(

            LiveJob(



                title=title,



                company_name=company_name,



                location=location,



                is_remote=is_remote,



                employment_type=(

                    employment_type

                ),



                seniority_level=(

                    seniority_level

                ),



                job_function="",



                industry=industry,



                description=description,



                experience_min=None,



                experience_max=None,



                posted_date=(

                    posted_date

                ),



                source_name="Jobicy",



                source_url=(

                    source_url

                ),



                application_url=(

                    source_url

                ),



                external_id=(

                    external_id

                ),



                source_type="jobicy",

            )

        )



    return jobs



def fetch_himalayas(profile: ProfileContext) -> list[LiveJob]:

    params: dict[str, Any] = {

        "q": profile.preferred_role or "software developer",

        "sort": "recent",

        "page": 1,

    }



    if profile.location:

        # Himalayas' country filter is a country, not a city.

        location_text = normalize_text(profile.location)



        if "india" in location_text:

            params["country"] = "India"



    data = fetch_json(

        "https://himalayas.app/jobs/api/search",

        params=params,

    )



    jobs: list[LiveJob] = []



    for item in data.get("jobs", [])[:MAX_JOBS_PER_SOURCE]:



        title = clean_text(

            item.get("title")

        )



        location = clean_text(

            item.get("location")

        )



        description = clean_text(

            item.get("description")

            or item.get("jobDescription")

        )



        # -----------------------------------------------------------

        # Himalayas may return many role aliases inside "category".

        #

        # Example:

        # "AI-Engineer, Game-Developer, Gameplay-Engineer, ..."

        #

        # job_function is a structured field, so store only the

        # first meaningful category instead of the complete alias list.

        # -----------------------------------------------------------



        raw_category = item.get("category")



        job_function = ""



        if isinstance(raw_category, list):

            for category in raw_category:

                category_text = clean_text(category)



                if category_text:

                    job_function = category_text

                    break



        elif isinstance(raw_category, dict):

            job_function = clean_text(

                raw_category.get("name")

                or raw_category.get("label")

                or raw_category.get("title")

            )



        else:

            category_text = clean_text(raw_category)



            if category_text:

                # Take only the first alias from a comma-separated

                # category string.

                first_category = re.split(

                    r",|;",

                    category_text,

                    maxsplit=1,

                )[0]



                job_function = clean_text(

                    first_category

                )



        # Convert source-style separators into readable text.

        job_function = re.sub(

            r"[-_]+",

            " ",

            job_function,

        ).strip()



        # Final defensive fallback.

        if not job_function:

            job_function = title



        # Keep this structured database field safely bounded.

        job_function = job_function[:255]



        jobs.append(

            LiveJob(

                title=title,

                company_name=clean_text(

                    item.get("companyName")

                    or (item.get("company") or {}).get("name")

                ),

                location=location,

                is_remote=True,

                employment_type=normalize_employment_type(

                    item.get("employmentType")

                ),

                seniority_level=clean_text(

                    item.get("seniority")

                ),

                job_function=job_function,

                industry="",

                description=description,

                posted_date=parse_date(

                    item.get("pubDate")

                    or item.get("created")

                    or item.get("datePosted")

                ),

                source_name="Himalayas",

                source_url=normalize_url(

                    item.get("applicationLink")

                    or item.get("url")

                    or item.get("guid")

                ),

                application_url=normalize_url(

                    item.get("applicationLink")

                    or item.get("url")

                ),

                external_id=str(

                    item.get("guid")

                    or item.get("id")

                    or ""

                ),

                source_type="himalayas",

            )

        )



    return jobs





def fetch_remote_ok(profile: ProfileContext) -> list[LiveJob]:

    data = fetch_json(

        "https://remoteok.com/api"

    )



    jobs: list[LiveJob] = []



    for item in data:

        if not isinstance(item, dict):

            continue



        # RemoteOK includes a metadata object as the first item.

        if not item.get("id") or not item.get("position"):

            continue



        title = clean_text(item.get("position"))

        description = clean_text(item.get("description"))

        location = clean_text(item.get("location"))



        jobs.append(

            LiveJob(

                title=title,

                company_name=clean_text(item.get("company")),

                location=location or "Remote",

                is_remote=True,

                employment_type="",

                seniority_level="",

                job_function=clean_text(item.get("category")),

                industry="",

                description=description,

                posted_date=parse_date(

                    item.get("date")

                    or item.get("epoch")

                ),

                source_name="Remote OK",

                source_url=normalize_url(item.get("url")),

                application_url=normalize_url(item.get("url")),

                external_id=str(item.get("id") or ""),

                source_type="remoteok",

            )

        )



        if len(jobs) >= MAX_JOBS_PER_SOURCE:

            break



    # Try to keep results related to profile skills/role.

    filtered = [

        job

        for job in jobs

        if matches_profile(job, profile)

    ]



    return filtered or jobs[:20]





def fetch_configured_company_source(

    source: dict[str, Any],

) -> list[LiveJob]:



    source_type = str(

        source.get("type", "")

    ).lower()



    if source_type == "greenhouse":

        return fetch_greenhouse(source)



    if source_type == "lever":

        return fetch_lever(source)



    if source_type == "ashby":

        return fetch_ashby(source)



    return []





def filter_and_dedupe(

    jobs: list[LiveJob],

    profile: ProfileContext,

) -> list[LiveJob]:



    unique: dict[str, LiveJob] = {}



    for job in jobs:

        if not job.title or not job.company_name:

            continue



        if not job.source_url:

            continue



        if not is_recent(job.posted_date):

            continue



        key = job_key(job)



        if key in unique:

            continue



        # For the first live-source implementation we are deliberately

        # conservative: only remove listings that are obviously unrelated.

        if job.source_type in {

            "jobicy",

            "himalayas",

            "remoteok",

        }:

            if not matches_profile(job, profile):

                continue



        unique[key] = job



    return list(unique.values())





def discover_live_jobs(

    profile: ProfileContext,

) -> tuple[list[LiveJob], list[str]]:



    sources = load_sources()



    jobs: list[LiveJob] = []

    errors: list[str] = []



    tasks = []



    with ThreadPoolExecutor(max_workers=6) as executor:

        tasks.append(

            executor.submit(

                fetch_jobicy,

                profile,

            )

        )



        tasks.append(

            executor.submit(

                fetch_himalayas,

                profile,

            )

        )



        tasks.append(

            executor.submit(

                fetch_remote_ok,

                profile,

            )

        )



        for source in sources:

            tasks.append(

                executor.submit(

                    fetch_configured_company_source,

                    source,

                )

            )



        for future in as_completed(tasks):

            try:

                jobs.extend(future.result())

            except Exception as exc:

                errors.append(

                    f"{type(exc).__name__}: {exc}"

                )



    return (

        filter_and_dedupe(

            jobs,

            profile,

        ),

        errors,

    )





@router.post(

    "/search/{profile_id}"

)

async def search_fresh_jobs(

    profile_id: int,

):

    if profile_id <= 0:

        raise HTTPException(

            status_code=400,

            detail="profile_id must be positive.",

        )



    try:

        # Use the existing synchronization service so fresh listings are
        # persisted in MySQL before the frontend reloads recommendations.
        from backend.app.live_job_sync import sync_profile_jobs

        sync_result = await __import__(
            "asyncio"
        ).to_thread(
            sync_profile_jobs,
            profile_id,
        )

        return {
            "status": "success",
            "profile_id": profile_id,
            "source_count": 3 + len(load_sources()),
            "job_count": sync_result["discovered"],
            "inserted": sync_result["inserted"],
            "updated_existing": sync_result["updated_existing"],
            "skipped": sync_result["skipped"],
            "unique_job_ids_in_sync": sync_result[
                "unique_job_ids_in_sync"
            ],
            "job_ids": sync_result["job_ids"],
            "skill_extraction": sync_result["skill_extraction"],
            "errors": sync_result["source_errors"],
            "message": (
                f"Fetched and synchronized {sync_result['discovered']} recent "
                "public job listings from the configured free sources."
            ),
        }



    except ValueError as exc:

        raise HTTPException(

            status_code=404,

            detail=str(exc),

        ) from exc



    except requests.RequestException as exc:

        raise HTTPException(

            status_code=502,

            detail=f"Live job source request failed: {exc}",

        ) from exc



    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=f"Live job source sync failed: {exc}",

        ) from exc
