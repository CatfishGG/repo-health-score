"""
CLI entry point for Repo Health Score.
"""

import argparse
import json
import os
import sys
from typing import Optional

from repo_health_score.scoring.scanner import scan_repo, ScannerConfig
from repo_health_score.scoring.engine import RepoHealthReport


def main():
    parser = argparse.ArgumentParser(
        prog="repo-health-score",
        description="Score the health of GitHub repositories. Get a single letter grade across dependencies, CI/CD, PRs, issues, community, and docs.",
    )

    parser.add_argument(
        "repo",
        nargs="?",
        help="Repository in format 'owner/repo'. Defaults to all repos for a user.",
    )
    parser.add_argument(
        "--token", "-t",
        help="GitHub Personal Access Token. Can also be set via GITHUB_TOKEN env var.",
        default=os.environ.get("GITHUB_TOKEN"),
    )
    parser.add_argument(
        "--all-repos",
        action="store_true",
        help="Scan all repositories for the authenticated user.",
    )
    parser.add_argument(
        "--user", "-u",
        help="Scan all repos for a specific user/org.",
    )
    parser.add_argument(
        "--output", "-o",
        choices=["json", "table", "summary"],
        default="summary",
        help="Output format.",
    )
    parser.add_argument(
        "--json-output",
        help="Write JSON output to a file.",
    )
    parser.add_argument(
        "--weights",
        help="Custom dimension weights as JSON. E.g. '{\"dependencies\":0.4,\"ci_cd\":0.1}'",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        help="Repos to exclude from scan (for --all-repos or --user).",
    )

    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: No GitHub token provided. Set GITHUB_TOKEN env var or use --token.")
        sys.exit(1)

    # Parse custom weights if provided
    custom_weights = None
    if args.weights:
        import json as json_lib
        try:
            custom_weights = json_lib.loads(args.weights)
        except Exception as e:
            print(f"Error: Invalid weights JSON: {e}")
            sys.exit(1)

    config = ScannerConfig(custom_weights=custom_weights)

    # If --all-repos or --user, scan multiple repos
    if args.all_repos or args.user:
        target = args.user or "me"
        _scan_all_repos(token, target, config, args)
        return

    # Single repo mode
    if not args.repo:
        print("Error: Either provide a repo (owner/repo) or use --all-repos / --user.")
        sys.exit(1)

    owner, repo = args.repo.split("/")

    print(f"Scanning {owner}/{repo}...")
    report = scan_repo(owner, repo, token, config)

    if args.output == "json":
        print(json.dumps(report.to_dict(), indent=2))
    elif args.output == "table":
        _print_table([report])
    else:
        _print_summary([report])

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\nJSON output written to {args.json_output}")


def _scan_all_repos(token: str, target: str, config: ScannerConfig, args):
    """Scan all repos for a user or org."""
    from repo_health_score.github.client import GitHubClient

    client = GitHubClient.from_pat(token)

    if target == "me":
        user_resp = client.session.get("https://api.github.com/user")
        user_resp.raise_for_status()
        username = user_resp.json().get("login")
    else:
        username = target

    print(f"Fetching repositories for {username}...")

    if target == "me" or target == username:
        repos_data = client.get_repos(username)
    else:
        repos_data = client.get_org_repos(username)

    # Filter out forks and archived if desired
    repos_data = [r for r in repos_data if not r.get("fork")]

    # Exclude specific repos
    if args.exclude:
        repos_data = [r for r in repos_data if r["name"] not in args.exclude]

    print(f"Found {len(repos_data)} repositories to scan.")

    reports: list[RepoHealthReport] = []

    for repo_info in repos_data:
        full_name = repo_info["full_name"]
        owner, repo = repo_info["owner"]["login"], repo_info["name"]

        try:
            print(f"  Scanning {full_name}...", end=" ", flush=True)
            report = scan_repo(owner, repo, token, config)
            reports.append(report)
            print(f"[{report.overall_letter} {report.overall_score:.1f}]")
        except Exception as e:
            print(f"[ERROR: {e}]")

    if not reports:
        print("No repositories could be scanned.")
        return

    if args.output == "json":
        print(json.dumps([r.to_dict() for r in reports], indent=2))
    elif args.output == "table":
        _print_table(reports)
    else:
        _print_summary(reports)

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump([r.to_dict() for r in reports], f, indent=2)
        print(f"\nJSON output written to {args.json_output}")


def _print_summary(reports: list[RepoHealthReport]):
    """Print a human-readable summary."""
    print("\n" + "=" * 60)
    print("REPO HEALTH SCORES")
    print("=" * 60)

    for report in sorted(reports, key=lambda r: r.overall_score):
        letter_color = _color_for_letter(report.overall_letter)
        print(f"\n{letter_color}{report.overall_letter}{_reset()} [{report.overall_score:.1f}/100] {report.owner}/{report.repo}")

        if report.recommendations:
            for rec in report.recommendations[:3]:
                print(f"  -> {rec}")

    print("\n" + "-" * 60)
    print(f"Scanned {len(reports)} repositories")
    print("=" * 60)


def _print_table(reports: list[RepoHealthReport]):
    """Print a table of scores."""
    print(f"\n{'Repo':<40} {'Score':>8} {'Letter':>8}")
    print("-" * 58)

    for report in sorted(reports, key=lambda r: r.overall_score):
        print(f"{report.owner}/{report.repo:<40} {report.overall_score:>7.1f} {report.overall_letter:>8}")


def _color_for_letter(letter: str) -> str:
    """Return ANSI color code for a letter grade."""
    colors = {
        "A": "\033[92m",  # Green
        "B": "\033[93m",  # Yellow
        "C": "\033[94m",  # Blue
        "D": "\033[93m",  # Yellow
        "F": "\033[91m",  # Red
    }
    return colors.get(letter, "")


def _reset() -> str:
    return "\033[0m"


if __name__ == "__main__":
    main()