"""
Main repository scanner.
Orchestrates all scoring dimensions for a single repo.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from ..github.client import GitHubClient
from .engine import HealthScorer, RepoHealthReport, DimensionScore
from . import dependencies, ci_cd, pulls, issues, community, documentation


@dataclass
class ScannerConfig:
    """Configuration for what dimensions to include and scoring weights."""

    include_dependencies: bool = True
    include_ci_cd: bool = True
    include_pull_requests: bool = True
    include_issues: bool = True
    include_community: bool = True
    include_documentation: bool = True

    custom_weights: Optional[dict] = None


def scan_repo(
    owner: str,
    repo: str,
    token: Optional[str] = None,
    config: Optional[ScannerConfig] = None,
    *,
    client: Optional[Any] = None,
) -> RepoHealthReport:
    """
    Scan a single repository and produce a health report.


    Args:
        owner: Repository owner (user or org)
        repo: Repository name
        token: GitHub personal access token (ignored if client is provided)
        config: Optional scanner configuration
        client: Optional pre-configured GitHubClient (or GitHubAppClientWrapper)
                If provided, token is ignored and the client is used directly.

    Returns:
        RepoHealthReport with all dimension scores and recommendations
    """
    if config is None:
        config = ScannerConfig()

    if client is not None:
        gh = client
    elif token is not None:
        gh = GitHubClient.from_pat(token)
    else:
        raise ValueError("Must provide either token or client")

    # Fetch all data in parallel where possible
    repo_data = gh.get_repo(owner, repo)
    default_branch = repo_data.get("default_branch", "main")

    # Dimension scores collection
    dimension_scores: list[DimensionScore] = []

    # === Dependencies ===
    if config.include_dependencies:
        try:
            dependabot_alerts = gh.get_dependabot_alerts(owner, repo)
            dep_score = dependencies.score_dependencies(dependabot_alerts)
            dimension_scores.append(dep_score)
        except Exception as e:
            # Dependabot might not be enabled — score conservatively
            dimension_scores.append(
                DimensionScore(
                    name="dependencies",
                    score=80.0,  # Assume OK if we can't check
                    weight=0.25,
                    details={"error": str(e), "note": "Could not fetch Dependabot data"},
                )
            )

    # === CI/CD ===
    if config.include_ci_cd:
        try:
            workflow_runs = gh.get_workflow_runs(owner, repo, per_page=30)
            ci_score = ci_cd.score_ci_cd(workflow_runs)
            dimension_scores.append(ci_score)
        except Exception as e:
            dimension_scores.append(
                DimensionScore(
                    name="ci_cd",
                    score=0.0,
                    weight=0.20,
                    details={"error": str(e)},
                )
            )

    # === Pull Requests ===
    if config.include_pull_requests:
        try:
            open_prs = gh.get_pulls(owner, repo, state="open")
            pr_score = pulls.score_pull_requests(open_prs)
            dimension_scores.append(pr_score)
        except Exception as e:
            dimension_scores.append(
                DimensionScore(
                    name="pull_requests",
                    score=0.0,
                    weight=0.20,
                    details={"error": str(e)},
                )
            )

    # === Issues ===
    if config.include_issues:
        try:
            open_issues = gh.get_issues(owner, repo, state="open")
            issue_score = issues.score_issues(open_issues)
            dimension_scores.append(issue_score)
        except Exception as e:
            dimension_scores.append(
                DimensionScore(
                    name="issues",
                    score=0.0,
                    weight=0.15,
                    details={"error": str(e)},
                )
            )

    # === Community ===
    if config.include_community:
        try:
            comm_score = community.score_community(repo_data, [], [])
            dimension_scores.append(comm_score)
        except Exception as e:
            dimension_scores.append(
                DimensionScore(
                    name="community",
                    score=0.0,
                    weight=0.10,
                    details={"error": str(e)},
                )
            )

    # === Documentation ===
    if config.include_documentation:
        try:
            readme_content = _fetch_readme(gh, owner, repo, default_branch)
            doc_score = documentation.score_documentation(repo_data, readme_content)
            dimension_scores.append(doc_score)
        except Exception as e:
            dimension_scores.append(
                DimensionScore(
                    name="documentation",
                    score=0.0,
                    weight=0.10,
                    details={"error": str(e)},
                )
            )

    # === Aggregate ===
    scorer = HealthScorer(custom_weights=config.custom_weights)
    overall_score, overall_letter = scorer.aggregate(dimension_scores)
    recommendations = scorer.generate_recommendations(dimension_scores)

    return RepoHealthReport(
        owner=owner,
        repo=repo,
        overall_score=overall_score,
        overall_letter=overall_letter,
        dimensions=dimension_scores,
        recommendations=recommendations,
        scanned_at=datetime.now(timezone.utc),
    )


def _fetch_readme(client: GitHubClient, owner: str, repo: str, default_branch: str) -> Optional[str]:
    """Fetch README content if it exists."""
    readme_names = [
        "README.md", "README.md", "README.txt",
        "readme.md", "Readme.md", "README.MD",
    ]

    for name in readme_names:
        try:
            resp = client.session.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{name}",
                params={"ref": default_branch},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data.get("encoding") == "base64":
                    import base64
                    content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
                    return content
        except Exception:
            continue

    return None