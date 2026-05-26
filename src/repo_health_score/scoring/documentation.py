"""
Documentation health scoring.
Measures README presence, doc freshness, and overall documentation quality.
"""

from datetime import datetime, timezone
from .engine import DimensionScore


def score_documentation(
    repo_data: dict,
    readme_content: str = None,
    last_doc_commit: str = None,
) -> DimensionScore:
    """
    Score documentation health.

    Args:
        repo_data: Full repo metadata dict from GitHub API
        readme_content: Optional README content for quality analysis
        last_doc_commit: Optional ISO timestamp of last doc update

    Returns:
        DimensionScore for documentation
    """
    score = 100.0
    details = {}

    # Check README existence
    has_readme = readme_content is not None or repo_data.get("has_wiki", False)
    details["has_readme"] = has_readme

    if not has_readme:
        score -= 30
        details["missing_readme"] = True

    # Check README content quality (basic heuristic)
    if readme_content:
        readme_length = len(readme_content)

        # Very short README
        if readme_length < 100:
            score -= 15
            details["readme_too_short"] = True

        # Check for common sections
        has_installation = any(
            keyword in readme_content.lower()
            for keyword in ["install", "setup", "getting started"]
        )
        has_usage = any(
            keyword in readme_content.lower()
            for keyword in ["usage", "example", "how to"]
        )
        has_contact = any(
            keyword in readme_content.lower()
            for keyword in ["contact", "author", "contribute"]
        )

        details["has_installation_section"] = has_installation
        details["has_usage_section"] = has_usage
        details["has_contact_section"] = has_contact

        # Missing key sections
        if not has_installation:
            score -= 10
        if not has_usage:
            score -= 10

    # Check for recent doc updates (using repo push date as proxy)
    pushed_at = repo_data.get("pushed_at")
    if pushed_at:
        try:
            last_push = datetime.fromisoformat(pushed_at.replace("Z", "+00:00")).replace(tzinfo=None)
            days_since_push = (datetime.now(timezone.utc).replace(tzinfo=None) - last_push).days
            details["last_push_days"] = days_since_push

            # If repo hasn't been pushed in a long time, docs are likely stale
            if days_since_push > 365:
                score -= 20
                details["repo_stale"] = True
            elif days_since_push > 180:
                score -= 10
                details["repo_somewhat_stale"] = True
        except Exception:
            pass

    # Check for wiki
    has_wiki = repo_data.get("has_wiki", False)
    details["has_wiki"] = has_wiki

    score = max(0.0, min(100.0, score))

    return DimensionScore(
        name="documentation",
        score=score,
        weight=0.10,
        details=details,
    )