"""
FastAPI development server for the Repo Health Score GitHub App.

Run with:
    python -m repo_health_score.github_app.app

Or via uvicorn for production:
    uvicorn repo_health_score.github_app.app:app --host 0.0.0.0 --port 8484

Required environment variables:
    GITHUB_APP_CLIENT_ID     — from GitHub App settings
    GITHUB_APP_CLIENT_SECRET — from GitHub App settings
    GITHUB_APP_APP_ID        — from GitHub App settings
    GITHUB_APP_PRIVATE_KEY   — contents of the privatekey.pem file

Optional:
    GITHUB_APP_REDIRECT_URI      — default: http://localhost:8484/oauth/callback
    GITHUB_APP_TOKEN_STORE       — path for token storage; default: ~/.repo_health_score/app_tokens.json
    GITHUB_APP_WEBHOOK_SECRET    — if set, webhook signatures are validated
"""

from __future__ import annotations

import os

import uvicorn

from repo_health_score.github_app.routes import create_app


def main():
    """Run the GitHub App FastAPI server."""
    app = create_app()

    host = os.environ.get("GITHUB_APP_HOST", "0.0.0.0")
    port = int(os.environ.get("GITHUB_APP_PORT", "8484"))

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
