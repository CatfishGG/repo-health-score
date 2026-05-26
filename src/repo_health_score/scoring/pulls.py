"""
Pull request health scoring.
Measures PR age, stale labels, review turnaround, and overall PR management.
"""

from datetime import datetime, timezone
from .engine import DimensionScore


def score_pull_requests(pulls: list[dict]) -> DimensionScore:
    """
    Score pull request health.

    Args:
        pulls: List of PR dicts from GitHub API

    Returns:
        DimensionScore for pull requests
    """
    if not pulls:
        return DimensionScore(
            name="pull_requests",
            score=100.0,
            weight=0.20,
            details={"note": "No open pull requests"},
        )

    now = datetime.now(timezone.utc)
    stale_threshold_days = 30
    very_stale_threshold_days = 60

    stale_prs = 0
    very_stale_prs = 0
    total_age_days = 0
    unreviewed = 0

    for pr in pulls:
        created_at = pr.get("created_at")
        if not created_at:
            continue

        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(tzinfo=None)
            age_days = (now.replace(tzinfo=None) - created).days
            total_age_days += age_days

            if age_days > very_stale_threshold_days:
                very_stale_prs += 1
            elif age_days > stale_threshold_days:
                stale_prs += 1

            # Check for unreviewed PRs (no reviews)
            if pr.get("review_comments", 0) == 0 and pr.get("comments", 0) == 0:
                unreviewed += 1

        except Exception:
            continue

    avg_age_days = total_age_days / len(pulls) if pulls else 0

    # Score: start at 100, penalise issues
    score = 100.0

    # Stale PRs penalty
    score -= stale_prs * 5
    score -= very_stale_prs * 10

    # High average age penalty
    if avg_age_days > 60:
        score -= 20
    elif avg_age_days > 30:
        score -= 10
    elif avg_age_days > 14:
        score -= 5

    # Unreviewed PRs penalty
    unreviewed_ratio = unreviewed / len(pulls)
    if unreviewed_ratio > 0.5:
        score -= 15
    elif unreviewed_ratio > 0.3:
        score -= 10

    score = max(0.0, min(100.0, score))

    details = {
        "open_prs": len(pulls),
        "stale_prs": stale_prs,
        "very_stale_prs": very_stale_prs,
        "unreviewed_prs": unreviewed,
        "avg_age_days": round(avg_age_days, 1),
        "stale_threshold_days": stale_threshold_days,
    }

    return DimensionScore(
        name="pull_requests",
        score=score,
        weight=0.20,
        details=details,
    )