"""
Community health scoring.
Measures contributors, contribution guidelines, and response rates.
"""

from .engine import DimensionScore


def score_community(repo_data: dict, pulls: list[dict], issues: list[dict]) -> DimensionScore:
    """
    Score community health.

    Args:
        repo_data: Full repo metadata dict from GitHub API
        pulls: List of PR dicts
        issues: List of issue dicts

    Returns:
        DimensionScore for community
    """
    score = 100.0
    details = {}

    # Check if repo is a fork (lower community score)
    is_fork = repo_data.get("fork", False)
    if is_fork:
        score -= 10
        details["is_fork"] = True

    # Check if it's an archived repo
    is_archived = repo_data.get("archived", False)
    if is_archived:
        score -= 20
        details["is_archived"] = True

    # Check for license (important for OSS community)
    has_license = repo_data.get("license") is not None
    if not has_license:
        score -= 10
        details["no_license"] = True

    # Check for contributing guidelines
    has_contributing = _check_file_exists(repo_data, ".github/ISSUE_TEMPLATE") or \
                       _check_file_exists(repo_data, ".github/PULL_REQUEST_TEMPLATE") or \
                       _check_file_exists(repo_data, "CONTRIBUTING.md")
    if not has_contributing:
        score -= 5
        details["no_contributing_guidelines"] = True

    # Check for issue templates
    has_issue_templates = _check_file_exists(repo_data, ".github/ISSUE_TEMPLATE")
    details["has_issue_templates"] = has_issue_templates

    # Check for PR templates
    has_pr_templates = _check_file_exists(repo_data, ".github/PULL_REQUEST_TEMPLATE")
    details["has_pr_templates"] = has_pr_templates

    # Count contributors (approximate, from the repo data)
    # Note: full contributor count requires separate API call
    has_contributors = repo_data.get("subscribers_count", 0) > 0 or \
                       repo_data.get("stargazers_count", 0) > 0
    details["contributors"] = 0  # Would need separate API call for accurate count

    # Response rate on PRs and issues (if data available)
    if pulls:
        reviewed = sum(1 for pr in pulls if pr.get("review_comments", 0) > 0 or pr.get("comments", 0) > 0)
        response_rate = reviewed / len(pulls)
        if response_rate < 0.5:
            score -= 10
        details["pr_response_rate"] = round(response_rate, 2)

    if issues:
        commented_issues = sum(1 for i in issues if i.get("comments", 0) > 0)
        response_rate = commented_issues / len(issues)
        if response_rate < 0.4:
            score -= 10
        details["issue_response_rate"] = round(response_rate, 2)

    score = max(0.0, min(100.0, score))

    details["has_license"] = has_license
    details["has_contributing_guidelines"] = has_contributing

    return DimensionScore(
        name="community",
        score=score,
        weight=0.10,
        details=details,
    )


def _check_file_exists(repo_data: dict, path: str) -> bool:
    """Check if a file or directory path exists in the repo.
    This is a simplified check based on repo metadata.
    """
    # We can't definitively check file existence without API calls
    # For now, return False as a default (conservative)
    return False