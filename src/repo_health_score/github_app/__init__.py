"""
GitHub App authentication and web server.

Components:
- auth       — OAuth flow + App installation tokens
- routes     — FastAPI web routes
- app        — Standalone development server entry point

Usage:
    # Start the server
    python -m repo_health_score.github_app.app

    # Use in CLI
    repo-health-score owner/repo --app
"""

from repo_health_score.github_app.auth import (
    GitHubAppAuthenticator,
    InstallationTokenInfo,
    OAuthTokenInfo,
)
from repo_health_score.github_app.routes import create_app

__all__ = [
    "GitHubAppAuthenticator",
    "InstallationTokenInfo",
    "OAuthTokenInfo",
    "create_app",
]
