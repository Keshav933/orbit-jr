import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.resume_parser import clean_resume_text


sample_text = """
Keshav Kumar


Python,     SQL,     React.js


Machine
Learning



Experience:
Software       Intern
"""


cleaned_text = clean_resume_text(sample_text)


print("Original text:")
print(sample_text)

print()
print("=" * 40)
print()

print("Cleaned text:")
print(cleaned_text)