import json
import re
from datetime import datetime
from pathlib import Path


RAW_FOLDER = Path("data/raw/role-radar")
PROCESSED_FOLDER = Path("data/processed/role-radar")


def clean_text(value):
    if not isinstance(value, str):
        return value

    value = value.replace("\r", " ")
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_list(values):
    if values is None:
        return []

    if not isinstance(values, list):
        values = [values]

    result = []

    for value in values:
        if isinstance(value, str):
            value = clean_text(value)

            if value:
                result.append(value)
        else:
            result.append(value)

    return result


def clean_number(value):
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_date(value):
    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return parsed.isoformat()
    except ValueError:
        return value


def clean_job(job):
    return {
        "id": str(job.get("id", "")).strip(),
        "title": clean_text(job.get("title", "")),
        "company": clean_text(job.get("company", "")),
        "location": clean_text(job.get("location", "")),
        "description": clean_text(job.get("description", "")),
        "seniority_level": clean_text(
            job.get("seniority_level", "")
        ),
        "employment_type": clean_text(
            job.get("employment_type", "")
        ),
        "job_function": clean_text(
            job.get("job_function", "")
        ),
        "industry": clean_text(
            job.get("industry", "")
        ),
        "url": clean_text(job.get("url", "")),
        "posted_at": clean_date(
            job.get("posted_at")
        ),
        "scraped_at": clean_date(
            job.get("scraped_at")
        ),
        "role_family_hint": clean_text(
            job.get("role_family_hint", "")
        ),
        "domain_hint": clean_text(
            job.get("domain_hint", "")
        ),
        "experience_years_hint": clean_number(
            job.get("experience_years_hint")
        ),
        "remote_hint": bool(
            job.get("remote_hint", False)
        ),
    }


def clean_profile(profile):
    return {
        "profile_id": str(
            profile.get("profile_id", "")
        ).strip(),
        "roles": clean_list(
            profile.get("roles")
        ),
        "skills_primary": clean_list(
            profile.get("skills_primary")
        ),
        "skills_secondary": clean_list(
            profile.get("skills_secondary")
        ),
        "experience_years": clean_number(
            profile.get("experience_years")
        ),
        "seniority": clean_text(
            profile.get("seniority", "")
        ),
        "domains": clean_list(
            profile.get("domains")
        ),
        "preferences": profile.get(
            "preferences"
        ),
        "career_intent": clean_text(
            profile.get("career_intent", "")
        ),
        "dealbreakers": clean_list(
            profile.get("dealbreakers")
        ),
    }


def load_json(file_name):
    file_path = RAW_FOLDER / file_name

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def save_json(file_name, data):
    file_path = PROCESSED_FOLDER / file_name

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


def normalize_id(value):
    if value is None:
        return ""

    return str(value).strip()


def find_duplicate_jobs(jobs):
    jobs_by_id = {}

    for job in jobs:
        job_id = job["id"]

        if not job_id:
            continue

        jobs_by_id.setdefault(
            job_id,
            []
        ).append(job)

    duplicates = {
        job_id: records
        for job_id, records
        in jobs_by_id.items()
        if len(records) > 1
    }

    return duplicates


PROCESSED_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


jobs = load_json("scraped_jobs.json")
profiles = load_json("synthetic_profiles.json")
pairs = load_json("phase3_pairs.json")
labels = load_json("phase3_labels.json")
gold_labels = load_json("gold_labels.json")


clean_jobs = [
    clean_job(job)
    for job in jobs
]

clean_profiles = [
    clean_profile(profile)
    for profile in profiles
]


clean_pairs = []

for pair in pairs:
    clean_pair = dict(pair)

    clean_pair["pair_id"] = normalize_id(
        pair.get("pair_id")
    )

    clean_pair["profile_id"] = normalize_id(
        pair.get("profile_id")
    )

    clean_pair["job_id"] = normalize_id(
        pair.get("job_id")
    )

    clean_pairs.append(clean_pair)


clean_labels = []

for label in labels:
    clean_label = dict(label)

    clean_label["pair_id"] = normalize_id(
        label.get("pair_id")
    )

    clean_labels.append(clean_label)


clean_gold_labels = []

for label in gold_labels:
    clean_label = dict(label)

    clean_label["pair_id"] = normalize_id(
        label.get("pair_id")
    )

    clean_gold_labels.append(clean_label)


save_json(
    "jobs_clean.json",
    clean_jobs
)

save_json(
    "profiles_clean.json",
    clean_profiles
)

save_json(
    "pairs_clean.json",
    clean_pairs
)

save_json(
    "labels_clean.json",
    clean_labels
)

save_json(
    "gold_labels_clean.json",
    clean_gold_labels
)


job_ids = {
    job["id"]
    for job in clean_jobs
    if job["id"]
}

profile_ids = {
    profile["profile_id"]
    for profile in clean_profiles
    if profile["profile_id"]
}

pair_ids = {
    pair["pair_id"]
    for pair in clean_pairs
    if pair["pair_id"]
}

label_pair_ids = {
    label["pair_id"]
    for label in clean_labels
    if label["pair_id"]
}


unknown_job_ids = [
    pair
    for pair in clean_pairs
    if pair["job_id"] not in job_ids
]


unknown_profile_ids = [
    pair
    for pair in clean_pairs
    if pair["profile_id"]
    not in profile_ids
]


labels_without_pair = (
    label_pair_ids - pair_ids
)


duplicate_jobs = find_duplicate_jobs(
    clean_jobs
)


print()
print("=" * 60)
print("ROLE RADAR VALIDATION")
print("=" * 60)

print()

print("Jobs:", len(clean_jobs))
print("Profiles:", len(clean_profiles))
print("Pairs:", len(clean_pairs))
print("Labels:", len(clean_labels))
print("Gold labels:", len(clean_gold_labels))

print()

print(
    "Unique job IDs:",
    len(job_ids)
)

print(
    "Duplicate job IDs:",
    len(duplicate_jobs)
)

print(
    "Unique profile IDs:",
    len(profile_ids)
)

print()

print(
    "Pairs with unknown job ID:",
    len(unknown_job_ids)
)

print(
    "Pairs with unknown profile ID:",
    len(unknown_profile_ids)
)

print(
    "Labels without phase3 pair:",
    len(labels_without_pair)
)

print()


if duplicate_jobs:

    print("DUPLICATE JOB DETAILS")
    print("-" * 60)

    shown = 0

    for job_id, records in duplicate_jobs.items():

        print()
        print("Job ID:", job_id)
        print("Number of records:", len(records))

        for record in records:

            print(
                "Title:",
                record["title"]
            )

            print(
                "Company:",
                record["company"]
            )

            print(
                "URL:",
                record["url"]
            )

        shown += 1

        if shown >= 10:
            break


if unknown_profile_ids:

    print()
    print(
        "UNKNOWN PROFILE EXAMPLE"
    )
    print("-" * 60)

    example = unknown_profile_ids[0]

    print(
        "Profile ID:",
        example["profile_id"]
    )

    print(
        "Job ID:",
        example["job_id"]
    )

print()
print(
    "Clean files saved to:",
    PROCESSED_FOLDER
)
print()