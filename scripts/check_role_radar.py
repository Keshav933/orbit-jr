import json
from pathlib import Path


DATA_FOLDER = Path("data/raw/role-radar")


files = [
    "scraped_jobs.json",
    "synthetic_profiles.json",
    "phase3_pairs.json",
    "phase3_labels.json",
    "gold_labels.json",
]


for file_name in files:
    file_path = DATA_FOLDER / file_name

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    print()
    print("=" * 50)
    print(file_name)

    if isinstance(data, list):
        print("Records:", len(data))

        if len(data) > 0:
            print("First record keys:")
            print(list(data[0].keys()))

    elif isinstance(data, dict):
        print("Type: dictionary")
        print("Keys:")
        print(list(data.keys()))

    else:
        print("Unknown data type")