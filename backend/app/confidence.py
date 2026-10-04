import statistics

from backend.app.evidence import (
    get_ranked_jobs_with_explanations,
)


def calculate_signal_agreement(job):
    """
    Measure how consistently the different ranking
    signals support the same recommendation.

    All ranking signals are expected to be in [0, 1].

    Lower variation = higher agreement.
    """

    signals = [
        float(job.get("hybrid_score", 0.0)),
        float(job.get("skill_coverage", 0.0)),
        float(job.get("experience_score", 0.0)),
        float(job.get("role_score", 0.0)),
        float(job.get("seniority_score", 0.0)),
        float(job.get("location_score", 0.0)),
        float(job.get("market_score", 0.0)),
    ]

    if len(signals) < 2:
        return 0.0

    standard_deviation = statistics.pstdev(
        signals
    )

    # Convert variation into agreement.
    #
    # 0.00 std -> 1.00 agreement
    # Larger std -> lower agreement
    agreement = 1.0 - (
        standard_deviation * 2.0
    )

    return max(
        0.0,
        min(1.0, agreement)
    )


def calculate_confidence(job):
    """
    Calculate heuristic recommendation confidence.

    This is NOT a calibrated probability.

    The current confidence uses:

        relevance score
        +
        skill coverage
        +
        evidence coverage
        +
        signal agreement
    """

    final_score = float(
        job.get("final_score", 0.0)
    )

    skill_coverage = float(
        job.get("skill_coverage", 0.0)
    )

    evidence_coverage = float(
        job.get("evidence_coverage", 0.0)
    )

    agreement = calculate_signal_agreement(
        job
    )

    confidence = (
        0.45 * final_score
        + 0.20 * skill_coverage
        + 0.25 * evidence_coverage
        + 0.10 * agreement
    )

    confidence = max(
        0.0,
        min(1.0, confidence)
    )

    return round(
        confidence,
        4,
    )


def get_confidence_label(confidence):
    """
    Convert the heuristic confidence into a simple
    human-readable label.
    """

    if confidence >= 0.75:
        return "high"

    if confidence >= 0.50:
        return "medium"

    return "low"


def get_ranked_jobs_with_confidence(
    profile_id,
    retrieval_k=50,
    top_k=10,
):
    """
    Get ranked jobs, evidence, skill gaps,
    and heuristic confidence.
    """

    jobs = get_ranked_jobs_with_explanations(
        profile_id,
        retrieval_k=retrieval_k,
        top_k=top_k,
    )

    results = []

    for job in jobs:

        confidence = calculate_confidence(
            job
        )

        job["confidence"] = confidence

        job["confidence_label"] = (
            get_confidence_label(
                confidence
            )
        )

        results.append(job)

    return results