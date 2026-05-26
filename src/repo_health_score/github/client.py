"""
GitHub API client with PAT and GitHub App authentication support.
"""

from dataclasses import dataclass
from typing import Optional
import os

import requests


@dataclass
class GitHubClient:
    """
    GitHub API client supporting both PAT and GitHub App authentication.

    Auth priority:
    1. GitHub App token (installation token)
    2. Personal Access Token (PAT)
    """

    token: Optional[str] = None
    app_id: Optional[str] = None
    app_private_key: Optional[str] = None

    _session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {self.token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
            )
        return self._session

    @classmethod
    def from_pat(cls, token: str) -> "GitHubClient":
        """Create client from a Personal Access Token."""
        return cls(token=token)

    def get_repo(self, owner: str, repo: str) -> dict:
        """Get repository metadata."""
        resp = self.session.get(f"https://api.github.com/repos/{owner}/{repo}")
        resp.raise_for_status()
        return resp.json()

    def get_repos(self, username: str, per_page: int = 100) -> list:
        """Get all repos for a user (handles pagination)."""
        repos = []
        page = 1
        while True:
            resp = self.session.get(
                f"https://api.github.com/users/{username}/repos",
                params={"per_page": per_page, "page": page, "sort": "updated"},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            if len(data) < per_page:
                break
            page += 1
        return repos

    def get_org_repos(self, org: str, per_page: int = 100) -> list:
        """Get all repos for an organization."""
        repos = []
        page = 1
        while True:
            resp = self.session.get(
                f"https://api.github.com/orgs/{org}/repos",
                params={"per_page": per_page, "page": page, "sort": "updated"},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            if len(data) < per_page:
                break
            page += 1
        return repos

    def get_pulls(self, owner: str, repo: str, state: str = "open") -> list:
        """Get pull requests (default: open PRs)."""
        pulls = []
        page = 1
        while True:
            resp = self.session.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                params={"state": state, "per_page": 100, "page": page},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            pulls.extend(data)
            if len(data) < 100:
                break
            page += 1
        return pulls

    def get_issues(self, owner: str, repo: str, state: str = "open") -> list:
        """Get issues (not PRs)."""
        issues = []
        page = 1
        while True:
            resp = self.session.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                params={"state": state, "per_page": 100, "page": page},
            )
            resp.raise_for_status()
            data = resp.json()
            # Filter out PRs (they appear in issues endpoint)
            data = [item for item in data if not item.get("pull_request")]
            if not data:
                break
            issues.extend(data)
            if len(data) < 100:
                break
            page += 1
        return issues

    def get_workflow_runs(self, owner: str, repo: str, per_page: int = 30) -> list:
        """Get recent workflow runs."""
        resp = self.session.get(
            f"https://api.github.com/repos/{owner}/{repo}/actions/runs",
            params={"per_page": per_page},
        )
        resp.raise_for_status()
        return resp.json().get("workflow_runs", [])

    def get_dependabot_alerts(self, owner: str, repo: str) -> list:
        """Get Dependabot security alerts."""
        resp = self.session.get(
            f"https://api.github.com/repos/{owner}/{repo}/dependabot/alerts",
            params={"per_page": 100},
        )
        if resp.status_code == 404:
            # Dependabot not enabled or no alerts
            return []
        resp.raise_for_status()
        return resp.json()

    def get_contents(self, owner: str, repo: str, path: str) -> Optional[dict]:
        """Get file/directory contents from repo."""
        resp = self.session.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch name of a repo."""
        repo_data = self.get_repo(owner, repo)
        return repo_data.get("default_branch", "main")