import re
from collections import defaultdict
from functools import lru_cache
from html import unescape

from backend.app.database import get_connection


# Very generic words that should not be treated as skills
# when they appear alone in a resume or job description.
GENERIC_WORDS = {
    "analysis",
    "application",
    "communication",
    "development",
    "experience",
    "knowledge",
    "management",
    "process",
    "project",
    "service",
    "skills",
    "software",
    "system",
    "technology",
    "testing",
    "work",
}


# Some ESCO labels are valid skills in a specific context,
# but are too ambiguous when matched as a single normal word.
AMBIGUOUS_SINGLE_WORDS = {
    "less",
}


# Aliases observed in live-job diagnostics that produced
# clear false positives when matched literally.
BLOCKED_LIVE_JOB_ALIASES = {
    "it",
    "re",
    "source",
    "patterns",
    "clean",
    "craft",
    "crafting",
    "brands",
    "debate",
    "saas",
}


# These markers identify obvious legal, privacy, diversity,
# or application boilerplate. We remove the specific sentence
# containing the marker, not the whole surrounding paragraph.
BOILERPLATE_SENTENCE_PATTERNS = (
    re.compile(
        r"[^.!?]*(?:equal opportunity employer|equal employment opportunity)[^.!?]*[.!?]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"[^.!?]*all qualified applicants[^.!?]*[.!?]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"[^.!?]*(?:reasonable accommodation|protected veteran|"
        r"domestic partner status|genetic predisposition|"
        r"medical condition|sexual orientation|gender identity|"
        r"gender expression)[^.!?]*[.!?]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"[^.!?]*religious grooming[^.!?]*[.!?]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"[^.!?]*non[- ]discrimination[^.!?]*[.!?]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"[^.!?]*anti[- ]discrimination[^.!?]*[.!?]?",
        re.IGNORECASE,
    ),
)


def normalize_text(text):
    """
    Normalize text before matching skills.
    """

    if not text:
        return ""

    text = str(text).lower()

    # Convert common separators to spaces.
    text = re.sub(r"[-_/]", " ", text)

    # Keep characters useful for technical skills:
    # +  -> C++
    # #  -> C#
    # .  -> Node.js
    text = re.sub(
        r"[^a-z0-9+#.\s]",
        " ",
        text,
    )

    # Remove unnecessary whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def clean_job_boilerplate(text):
    """
    Remove only clear non-job boilerplate.

    The earlier cleaner removed an entire paragraph when it
    contained one boilerplate marker. That was too aggressive
    for live feeds because a paragraph can contain both real
    requirements and legal/application text.

    This version removes:
        1. HTML tags while preserving text boundaries.
        2. The trailing anti-spam instruction.
        3. Only sentences containing strong legal/privacy markers.

    Normal job responsibilities and requirements are preserved.
    """

    if not text:
        return ""

    text = unescape(str(text))

    # Preserve boundaries before removing HTML tags.
    text = re.sub(
        r"<\s*(?:br|/p|/li|/div|/h[1-6])\s*/?\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    # Remove remaining HTML tags.
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # RemoteOK and some other feeds append an anti-spam
    # instruction at the end of the description. Remove only
    # that instruction and anything after it.
    text = re.sub(
        r"\bplease mention the word\b.*$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove only individual sentences containing strong
    # legal/privacy/diversity boilerplate markers.
    for pattern in BOILERPLATE_SENTENCE_PATTERNS:
        text = pattern.sub(" ", text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def tokenize(text):
    """
    Convert normalized text into tokens.

    Examples:
        MySQL.  -> mysql
        Node.js -> node.js
        C++     -> c++
        C#      -> c#
    """

    text = normalize_text(text)

    return re.findall(
        r"[a-z0-9+#]+(?:\.[a-z0-9+#]+)*",
        text,
    )


@lru_cache(maxsize=1)
def load_skill_aliases():
    """
    Load ESCO aliases from MySQL.

    Returns:
        {
            "python": [
                {
                    "skill_id": 11173,
                    "skill_name": "Python (computer programming)",
                    "matched_alias": "Python"
                }
            ]
        }
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            sa.alias,
            s.id AS skill_id,
            s.name AS skill_name
        FROM skill_aliases sa
        JOIN skills s
            ON s.id = sa.skill_id
    """

    try:
        cursor.execute(query)
        rows = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    alias_map = defaultdict(list)

    for row in rows:
        alias = row["alias"]

        normalized_alias = normalize_text(alias)

        if not normalized_alias:
            continue

        # Skip aliases verified as problematic in
        # live-job diagnostics.
        if normalized_alias in BLOCKED_LIVE_JOB_ALIASES:
            continue

        alias_tokens = normalized_alias.split()

        # Ignore extremely short aliases.
        if len(normalized_alias) < 2:
            continue

        # Ignore generic/ambiguous single-word aliases.
        if (
            len(alias_tokens) == 1
            and (
                normalized_alias in GENERIC_WORDS
                or normalized_alias in AMBIGUOUS_SINGLE_WORDS
            )
        ):
            continue

        alias_map[normalized_alias].append(
            {
                "skill_id": row["skill_id"],
                "skill_name": row["skill_name"],
                "matched_alias": alias,
            }
        )

    # Resolve ambiguous aliases.
    #
    # Example:
    #
    # SQL
    # ├── SQL
    # └── database management systems
    #
    # Because "SQL" is itself a canonical skill,
    # keep only the exact canonical match.
    for alias, matches in list(alias_map.items()):

        exact_matches = []

        for match in matches:
            canonical_name = normalize_text(
                match["skill_name"]
            )

            if canonical_name == alias:
                exact_matches.append(match)

        if exact_matches:
            alias_map[alias] = exact_matches

        elif len(matches) > 1:
            # No exact canonical match and multiple concepts.
            #
            # Rather than creating an unreliable match,
            # ignore this ambiguous alias.
            del alias_map[alias]

    return alias_map


def extract_skills_from_text(text):
    """
    Extract skills from text using lexical alias matching.

    Obvious boilerplate is removed conservatively before
    matching. Only targeted legal/application sentences are
    removed; normal job text is preserved.

    Returns:
        [
            {
                "skill_id": 4915,
                "skill_name": "SQL",
                "matched_aliases": ["SQL"]
            }
        ]
    """

    if not text:
        return []

    text = clean_job_boilerplate(text)

    if not text:
        return []

    alias_map = load_skill_aliases()

    tokens = tokenize(text)

    if not tokens:
        return []

    # Find the largest alias phrase.
    max_alias_words = 1

    for alias in alias_map:
        word_count = len(alias.split())

        if word_count > max_alias_words:
            max_alias_words = word_count

    detected = {}

    # Check every possible phrase in the tokenized text.
    for i in range(len(tokens)):

        max_size = min(
            max_alias_words,
            len(tokens) - i,
        )

        for size in range(1, max_size + 1):

            phrase = " ".join(
                tokens[i:i + size]
            )

            matches = alias_map.get(phrase)

            if not matches:
                continue

            for match in matches:

                skill_id = match["skill_id"]

                if skill_id not in detected:
                    detected[skill_id] = {
                        "skill_id": skill_id,
                        "skill_name": match["skill_name"],
                        "matched_aliases": set(),
                    }

                detected[skill_id]["matched_aliases"].add(
                    match["matched_alias"]
                )

    result = []

    for skill in detected.values():

        skill["matched_aliases"] = sorted(
            skill["matched_aliases"]
        )

        result.append(skill)

    # Make output deterministic.
    result.sort(
        key=lambda item: item["skill_name"].lower()
    )

    return result
