"""
Issue health scoring.
Measures issue age, stale labels, and response turnaround.
"""

from datetime import datetime
from .engine import DimensionScore


def score_issues(issues: list[dict]) -> DimensionScore:
    """
    Score issue health.

    Args:
        issues: List of issue dicts from GitHub API

    Returns:
        DimensionScore for issues
    """
    if not issues:
        return DimensionScore(
            name="issues",
            score=100.0,
            weight=0.15,
            details={"note": "No open issues"},
        )

    now = datetime.utcnow()
    stale_threshold_days = 60
    very_stale_threshold_days = 120

    stale_issues = 0
    very_stale_issues = 0
    total_age_days = 0
    no_comments = 0

    for issue in issues:
        created_at = issue.get("created_at")
        if not created_at:
            continue

        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age_days = (now - created.replace(tzinfo=None)).days
            total_age_days += age_days

            if age_days > very_stale_threshold_days:
                very_stale_issues += 1
            elif age_days > stale_threshold_days:
                stale_issues += 1

            # Check for issues with no comments (possible abandonment)
            if issue.get("comments", 0) == 0:
                no_comments += 1

        except Exception:
            continue

    avg_age_days = total_age_days / len(issues) if issues else 0

    # Score: start at 100, penalise issues
    score = 100.0

    stale_ratio = stale_issues / len(issues)
    very_stale_ratio = very_stale_issues / len(issues)

    score -= stale_issues * 4
    score -= very_stale_issues * 8

    # High average age penalty
    if avg_age_days > 90:
        score -= 20
    elif avg_age_days > 60:
        score -= 10
    elif avg_age_days > 30:
        score -= 5

    # No-response issues penalty
    no_response_ratio = no_comments / len(issues)
    if no_response_ratio > 0.6:
        score -= 15
    elif no_response_ratio > 0.4:
        score -= 10

    score = max(0.0, min(100.0, score))

    details = {
        "open_issues": len(issues),
        "stale_issues": stale_issues,
        "very_stale_issues": very_stale_issues,
        "no_response_issues": no_comments,
        "avg_age_days": round(avg_age_days, 1),
        "stale_threshold_days": stale_threshold_days,
    }

    return DimensionScore(
        name="issues",
        score=score,
        weight=0.15,
        details=details,
    )