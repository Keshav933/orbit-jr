import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.database import get_connection


TECHNICAL_SKILLS = [
    {
        "name": "React",
        "aliases": ["React", "ReactJS", "React.js"],
    },
    {
        "name": "Node.js",
        "aliases": ["Node.js", "NodeJS", "Node JS"],
    },
    {
        "name": "Express.js",
        "aliases": ["Express.js", "ExpressJS", "Express"],
    },
    {
        "name": "Docker",
        "aliases": ["Docker", "Docker containers"],
    },
    {
        "name": "Git",
        "aliases": ["Git", "Git version control"],
    },
    {
        "name": "GitHub",
        "aliases": ["GitHub"],
    },
    {
        "name": "REST API",
        "aliases": [
            "REST API",
            "REST APIs",
            "RESTful API",
            "RESTful APIs",
        ],
    },
    {
        "name": "TypeScript",
        "aliases": ["TypeScript", "TS"],
    },
    {
        "name": "HTML",
        "aliases": ["HTML", "HTML5"],
    },
    {
        "name": "CSS",
        "aliases": ["CSS", "CSS3"],
    },
    {
        "name": "Tailwind CSS",
        "aliases": ["Tailwind CSS", "Tailwind"],
    },
    {
        "name": "Next.js",
        "aliases": ["Next.js", "NextJS"],
    },
    {
        "name": "Angular",
        "aliases": ["Angular", "AngularJS"],
    },
    {
        "name": "Vue.js",
        "aliases": ["Vue.js", "VueJS", "Vue"],
    },
    {
        "name": "FastAPI",
        "aliases": ["FastAPI"],
    },
    {
        "name": "Flask",
        "aliases": ["Flask"],
    },
    {
        "name": "Django",
        "aliases": ["Django"],
    },
    {
        "name": "MongoDB",
        "aliases": ["MongoDB", "Mongo DB"],
    },
    {
        "name": "PostgreSQL",
        "aliases": ["PostgreSQL", "Postgres"],
    },
    {
        "name": "Redis",
        "aliases": ["Redis"],
    },
    {
        "name": "MySQL",
        "aliases": ["MySQL"],
    },
    {
        "name": "Kubernetes",
        "aliases": ["Kubernetes", "K8s"],
    },
    {
        "name": "Linux",
        "aliases": ["Linux"],
    },
    {
        "name": "AWS",
        "aliases": [
            "AWS",
            "Amazon Web Services",
        ],
    },
    {
        "name": "Microsoft Azure",
        "aliases": [
            "Microsoft Azure",
            "Azure",
        ],
    },
    {
        "name": "Google Cloud",
        "aliases": [
            "Google Cloud",
            "Google Cloud Platform",
            "GCP",
        ],
    },
    {
        "name": "TensorFlow",
        "aliases": ["TensorFlow"],
    },
    {
        "name": "PyTorch",
        "aliases": ["PyTorch", "Pytorch"],
    },
    {
        "name": "scikit-learn",
        "aliases": [
            "scikit-learn",
            "scikit learn",
            "sklearn",
        ],
    },
    {
        "name": "NumPy",
        "aliases": ["NumPy", "Numpy"],
    },
    {
        "name": "Pandas",
        "aliases": ["Pandas"],
    },
    {
        "name": "Machine Learning",
        "aliases": [
            "Machine Learning",
            "ML",
        ],
    },
    {
        "name": "Deep Learning",
        "aliases": [
            "Deep Learning",
            "DL",
        ],
    },
    {
        "name": "Natural Language Processing",
        "aliases": [
            "Natural Language Processing",
            "NLP",
        ],
    },
]


def normalize_text(text):
    if not text:
        return ""

    return " ".join(
        str(text).strip().lower().split()
    )


def insert_skill(cursor, name):
    cursor.execute(
        """
        INSERT INTO skills
        (
            name,
            category,
            esco_uri
        )
        VALUES
        (
            %s,
            'technical',
            NULL
        )
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id)
        """,
        (name,),
    )

    return cursor.lastrowid


def insert_alias(
    cursor,
    skill_id,
    alias,
):
    normalized_alias = normalize_text(
        alias
    )

    if not normalized_alias:
        return

    cursor.execute(
        """
        INSERT IGNORE INTO skill_aliases
        (
            skill_id,
            alias,
            normalized_alias,
            source
        )
        VALUES
        (
            %s,
            %s,
            %s,
            'custom'
        )
        """,
        (
            skill_id,
            alias,
            normalized_alias,
        ),
    )


def main():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        total_skills = 0
        total_aliases = 0

        for item in TECHNICAL_SKILLS:

            skill_id = insert_skill(
                cursor,
                item["name"],
            )

            total_skills += 1

            # Always include the canonical name.
            all_aliases = set(
                [item["name"]]
                + item["aliases"]
            )

            for alias in all_aliases:

                insert_alias(
                    cursor,
                    skill_id,
                    alias,
                )

                total_aliases += 1

        connection.commit()

        print(
            "Technical skill import completed."
        )

        print(
            f"Technical skills processed: "
            f"{total_skills}"
        )

        print(
            f"Alias records processed: "
            f"{total_aliases}"
        )

    except Exception as error:
        connection.rollback()

        print(
            "Technical skill import failed."
        )

        print(error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
    