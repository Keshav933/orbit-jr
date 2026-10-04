import json
from pathlib import Path


INPUT_FILE = Path(
    "data/processed/role-radar/jobs_clean.json"
)

OUTPUT_FILE = Path(
    "data/processed/role-radar/jobs_final.json"
)


with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as file:
    jobs = json.load(file)


unique_jobs = {}
duplicate_count = 0


for job in jobs:
    job_id = job.get("id")

    if not job_id:
        continue

    if job_id in unique_jobs:
        duplicate_count += 1
        continue

    unique_jobs[job_id] = job


final_jobs = list(unique_jobs.values())


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:
    json.dump(
        final_jobs,
        file,
        ensure_ascii=False,
        indent=2
    )


print("Final job preparation completed.")
print()
print("Original jobs:", len(jobs))
print("Duplicate jobs removed:", duplicate_count)
print("Final unique jobs:", len(final_jobs))
print()
print("Saved to:")
print(OUTPUT_FILE)