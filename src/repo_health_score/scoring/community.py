"""
Community health scoring.
Measures contributors, contribution guidelines, and response rates.
"""

from typing import TYPE_CHECKING, Optional
from .engine import DimensionScore

if TYPE_CHECKING:
    from ..github.client import GitHubClient


def score_community(
    repo_data: dict,
    pulls: list[dict],
    issues: list[dict],
    *,
    client: Optional["GitHubClient"] = None,
) -> DimensionScore:
    """
    Score community health.

    Args:
        repo_data: Full repo metadata dict from GitHub API
        pulls: List of PR dicts
        issues: List of issue dicts
        client: Optional GitHubClient for file existence checks

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

    # Check for contributing guidelines, issue templates, PR templates
    owner = repo_data.get("owner", {}).get("login", "") or repo_data.get("full_name", "").split("/")[0]
    repo_name = repo_data.get("name", "")

    has_contributing = False
    has_issue_templates = False
    has_pr_templates = False

    if client and owner and repo_name:
        has_contributing = _check_file_exists(client, owner, repo_name, "CONTRIBUTING.md")
        has_issue_templates = _check_file_exists(client, owner, repo_name, ".github/ISSUE_TEMPLATE")
        has_pr_templates = _check_file_exists(client, owner, repo_name, ".github/PULL_REQUEST_TEMPLATE.md")

    if not has_contributing:
        score -= 5
        details["no_contributing_guidelines"] = True

    details["has_issue_templates"] = has_issue_templates
    details["has_pr_templates"] = has_pr_templates

    # Count contributors (approximate, from the repo data)
    has_contributors = repo_data.get("subscribers_count", 0) > 0 or \
                       repo_data.get("stargazers_count", 0) > 0
    details["contributors"] = 0  # Would need separate API call for accurate count

    # Response rate on PRs and issues (if data available)
    if pulls:
        reviewed = sum(
            1 for pr in pulls
            if pr.get("review_comments", 0) > 0 or pr.get("comments", 0) > 0
        )
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


def _check_file_exists(client: "GitHubClient", owner: str, repo: str, path: str) -> bool:
    """
    Check if a file or directory exists in the repo via the GitHub Contents API.
    """
    try:
        resp = client.session.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers={"Accept": "application/vnd.github+json"},
        )
        return resp.status_code == 200
    except Exception:
        return False
