import csv
from pathlib import Path


FILE_PATH = Path(
    "data/raw/esco/skills_en.csv"
)


rows = []

with open(
    FILE_PATH,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.DictReader(file)

    for row in reader:
        rows.append(row)


print("Total ESCO records:", len(rows))


preferred_labels = [
    row["preferredLabel"].strip()
    for row in rows
    if row.get("preferredLabel")
]


print(
    "Unique preferred labels:",
    len(set(preferred_labels))
)


print()
print("Checking common CSE skills:")
print()


search_words = [
    "python",
    "sql",
    "react",
    "java",
    "machine learning",
    "docker"
]


for word in search_words:

    matches = []

    for row in rows:

        label = row.get(
            "preferredLabel",
            ""
        ).lower()

        if word in label:
            matches.append(
                row["preferredLabel"]
            )

    print(word, "->", matches[:10])


print()
print("Example alternative labels:")
print()


shown = 0

for row in rows:

    alt_labels = row.get(
        "altLabels",
        ""
    ).strip()

    if alt_labels:

        print(
            "Preferred:",
            row["preferredLabel"]
        )

        print(
            "Alternative:",
            alt_labels
        )

        print()

        shown += 1

        if shown == 5:
            break