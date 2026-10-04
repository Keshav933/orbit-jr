import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.skill_extractor import (
    extract_skills_from_text
)


resume_text = """
Computer Science student with experience in Python,
SQL, Java, JavaScript and machine learning.

Developed web applications using React and worked
with MySQL databases.

Built REST APIs and worked on data analysis projects.
"""


skills = extract_skills_from_text(resume_text)

print("\nDetected skills:")
print("-" * 40)

for skill in skills:
    print(
        f"{skill['skill_name']} "
        f"-> {skill['matched_aliases']}"
    )

print("-" * 40)
print(f"Total detected skills: {len(skills)}")