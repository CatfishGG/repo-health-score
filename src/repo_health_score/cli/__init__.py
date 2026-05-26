"""
CLI entry point for Repo Health Score.
"""

import argparse
import json
import os
import sys
from typing import Optional

import requests

from repo_health_score.github.client import GitHubClient
from repo_health_score.scoring.scanner import scan_repo, ScannerConfig
from repo_health_score.scoring.engine import RepoHealthReport


def _get_github_client(token: str) -> "GitHubClient":
    """Create a GitHub client from a PAT."""
    from repo_health_score.github.client import GitHubClient
    return GitHubClient.from_pat(token)


def _get_app_client() -> "GitHubClient":
    """
    Create a GitHub client authenticated via GitHub App.
    Raises ValueError if App credentials are missing or no installation is found.
    """
    from repo_health_score.github_app.auth import GitHubAppAuthenticator
    from repo_health_score.github.client import GitHubClient

    auth = GitHubAppAuthenticator()

    # Load stored OAuth token to know the target account
    token_info = auth.load_oauth_token("default")
    if not token_info:
        raise ValueError(
            "No GitHub App OAuth token found. Run `python -m repo_health_score.github_app.app` "
            "and open http://localhost:8484/install to authenticate first."
        )

    # For now, use the OAuth token to determine which installation to use.
    # The CLI needs owner/repo to look up the installation.
    return GitHubAppClientWrapper(auth)


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
        "--app",
        action="store_true",
        help="Use GitHub App authentication instead of PAT. "
             "Requires GITHUB_APP_* environment variables and prior OAuth link via "
             "python -m repo_health_score.github_app.app",
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

    # Server options (used with serve command)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the web server to (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the web server on (default: 8000).",
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["serve", "scan"],
        help="Command to run: 'serve' starts the web server.",
    )

    args = parser.parse_args()

    # Handle serve command
    if args.command == "serve":
        _run_server(args)
        return

    token = args.token or os.environ.get("GITHUB_TOKEN")
    use_app = args.app

    if use_app:
        client = _get_app_client()
        token = "<github-app>"
    elif not token:
        print("Error: No GitHub token provided. Set GITHUB_TOKEN env var or use --token.", file=sys.stderr)
        print("Or use --app for GitHub App authentication.", file=sys.stderr)
        sys.exit(1)

    # Parse custom weights if provided
    custom_weights = None
    if args.weights:
        import json as json_lib
        try:
            custom_weights = json_lib.loads(args.weights)
        except Exception as e:
            print(f"Error: Invalid weights JSON: {e}", file=sys.stderr)
            sys.exit(1)

    config = ScannerConfig(custom_weights=custom_weights)

    # If --all-repos or --user, scan multiple repos
    if args.all_repos or args.user:
        target = args.user or "me"
        _scan_all_repos(token, target, config, args, use_app=use_app)
        return

    # Single repo mode
    if not args.repo:
        print("Error: Either provide a repo (owner/repo) or use --all-repos / --user.", file=sys.stderr)
        sys.exit(1)

    owner, repo = args.repo.split("/")

    print(f"Scanning {owner}/{repo}...")
    if use_app:
        report = scan_repo(owner, repo, client=client, config=config)
    else:
        report = scan_repo(owner, repo, token, config=config)

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


def _run_server(args):
    """Run the FastAPI web server."""
    import uvicorn

    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", 8000)

    print(f"Starting Repo Health Score API server on {host}:{port}")
    uvicorn.run(
        "repo_health_score.github_app.app:app",
        host=host,
        port=port,
        reload=False,
    )


def _scan_all_repos(token: str, target: str, config: ScannerConfig, args, use_app: bool = False):
    """Scan all repos for a user or org."""
    from repo_health_score.github.client import GitHubClient


    if use_app:
        scanner_client = _get_app_client()
        scanner_token = "<github-app>"
    else:
        scanner_client = GitHubClient.from_pat(token)
        scanner_token = token

    if target == "me":
        user_resp = scanner_client.session.get("https://api.github.com/user")
        user_resp.raise_for_status()
        username = user_resp.json().get("login")
    else:
        username = target

    print(f"Fetching repositories for {username}...")

    if target == "me" or target == username:
        repos_data = scanner_client.get_repos(username)
    else:
        repos_data = scanner_client.get_org_repos(username)

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
            if use_app:
                report = scan_repo(owner, repo, client=scanner_client, config=config)
            else:
                report = scan_repo(owner, repo, scanner_token, config=config)
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


class GitHubAppClientWrapper:
    """
    Thin wrapper that intercepts session/token access so our GitHubClient
    logic works seamlessly with a GitHub App installation token.

    The scan_repo function still expects (owner, repo, token) positional args,
    but we intercept the session/header setup to inject the installation token.
    """

    def __init__(self, auth: "GitHubAppAuthenticator"):
        self.auth = auth
        self._client: Optional[GitHubClient] = None
        # Look up the installation ID at startup
        self.installation_ids: list[str] = []
        self._resolve_installations()

    def _resolve_installations(self):
        """Discover all installations for this GitHub App."""
        jwt_token = self.auth.get_app_jwt()
        resp = requests.get(
            "https://api.github.com/app/installations",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        resp.raise_for_status()
        for install in resp.json():
            self.installation_ids.append(str(install["id"]))


    def _get_active_client(self, owner: str, repo: str) -> tuple[GitHubClient, str]:
        """
        Return a GitHubClient configured with a valid installation token
        for the given repo, and the installation_id.
        """
        token_info = self.auth.get_installation_token_for_repo(owner, repo)
        client = GitHubClient(token=token_info.token)
        return client, token_info.installation_id

    def __getattr__(self, name: str):
        """
        Proxy attribute access to a per-repo client.
        The CLI calls methods like get_repo(), get_repos(), etc.
        We pick a default installation for discovery, then switch based on the target repo.
        """
        if not self.installation_ids:
            raise ValueError("No GitHub App installations found. Is the app installed?")
        # Use the first installation for broad discovery
        installation_id = self.installation_ids[0]
        token_info = self.auth.get_installation_token(installation_id)
        client = GitHubClient(token=token_info.token)
        return getattr(client, name)


def _get_app_client():
    from repo_health_score.github_app.auth import GitHubAppAuthenticator
    return GitHubAppClientWrapper(GitHubAppAuthenticator())


if __name__ == "__main__":
    main()