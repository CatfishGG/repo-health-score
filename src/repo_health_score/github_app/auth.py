"""
GitHub App authentication module.

Handles:
- OAuth authorization code flow
- GitHub App installation token generation
- Secure token storage
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
import requests


# ─── Token storage helpers ────────────────────────────────────────────────────

def _token_store_path() -> Path:
    """Path where OAuth tokens are persisted."""
    return Path(os.environ.get("GITHUB_APP_TOKEN_STORE", str(Path.home() / ".repo_health_score" / "app_tokens.json")))


def _ensure_token_dir() -> Path:
    path = _token_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_token_store() -> dict:
    """Load the token store from disk, or return empty dict."""
    path = _token_store_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _save_token_store(store: dict) -> None:
    """Persists token store to disk."""
    path = _ensure_token_dir()
    path.write_text(json.dumps(store, indent=2))


# ─── Credential helpers ──────────────────────────────────────────────────────

def _get_app_credentials() -> tuple[str, str, str]:
    """Return (client_id, client_secret, private_key) from environment."""
    client_id = os.environ.get("GITHUB_APP_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_APP_CLIENT_SECRET")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY")

    missing = []
    if not client_id:
        missing.append("GITHUB_APP_CLIENT_ID")
    if not client_secret:
        missing.append("GITHUB_APP_CLIENT_SECRET")
    if not private_key:
        missing.append("GITHUB_APP_PRIVATE_KEY")

    if missing:
        raise ValueError(
            f"Missing GitHub App environment variables: {', '.join(missing)}. "
            "Set them before using GitHub App authentication."
        )

    return client_id, client_secret, private_key


def _get_app_id() -> str:
    """Return GITHUB_APP_APP_ID from environment."""
    app_id = os.environ.get("GITHUB_APP_APP_ID")
    if not app_id:
        raise ValueError("GITHUB_APP_APP_ID environment variable is not set.")
    return app_id


# ─── JWT generation for GitHub App ───────────────────────────────────────────

def _generate_jwt(app_id: str, private_key: str) -> str:
    """Generate a short-lived JWT for the GitHub App."""
    now = datetime.now(timezone.utc)
    payload = {
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=9)).timestamp()),
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class OAuthTokenInfo:
    """Represents a stored OAuth access token for a user/org."""
    access_token: str
    token_type: str
    scope: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_dict(cls, data: dict) -> "OAuthTokenInfo":
        # Parse created_at if present
        created = data.get("created_at")
        if created:
            if isinstance(created, str):
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
        else:
            created = datetime.now(timezone.utc)
        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "bearer"),
            scope=data.get("scope", ""),
            created_at=created,
        )

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class InstallationTokenInfo:
    """Represents a stored installation access token."""
    token: str
    installation_id: str
    app_id: str
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        # Consider expired 5 minutes before actual expiry for safety buffer
        safe_margin = timedelta(minutes=5)
        return datetime.now(timezone.utc) > (self.expires_at - safe_margin)

    @classmethod
    def from_dict(cls, data: dict) -> "InstallationTokenInfo":
        expires = data.get("expires_at", "")
        if isinstance(expires, str):
            expires_at = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        created = data.get("created_at")
        if created:
            if isinstance(created, str):
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
        else:
            created = datetime.now(timezone.utc)
        return cls(
            token=data["token"],
            installation_id=data["installation_id"],
            app_id=data["app_id"],
            expires_at=expires_at,
            created_at=created,
        )

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "installation_id": self.installation_id,
            "app_id": self.app_id,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


# ─── GitHub App Authenticator ─────────────────────────────────────────────────

class GitHubAppAuthenticator:
    """
    Full GitHub App + OAuth authenticator.

    Responsibilities:
    1. OAuth flow — exchange authorization code for user access token
    2. App installation flow — generate installation tokens for API calls
    3. Token caching — store tokens in a simple JSON file
    """

    GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_API_URL = "https://api.github.com"

    def __init__(self):
        self._client_id: Optional[str] = None
        self._client_secret: Optional[str] = None
        self._app_id: Optional[str] = None
        self._private_key: Optional[str] = None
        self.redirect_uri = os.environ.get("GITHUB_APP_REDIRECT_URI", "http://localhost:8484/oauth/callback")

    # ── Credential loading ─────────────────────────────────────────────────────

    def _ensure_credentials(self) -> None:
        """Load credentials from environment (cached on first call)."""
        if self._client_id is None:
            self._client_id, self._client_secret, self._private_key = _get_app_credentials()
            self._app_id = _get_app_id()

    @property
    def client_id(self) -> str:
        self._ensure_credentials()
        return self._client_id  # type: ignore

    @property
    def app_id(self) -> str:
        self._ensure_credentials()
        return self._app_id  # type: ignore

    @property
    def private_key(self) -> str:
        self._ensure_credentials()
        return self._private_key  # type: ignore

    # ── OAuth flow ─────────────────────────────────────────────────────────────

    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Build the GitHub OAuth authorization URL.
        Returns (url, state) — state should be stored and validated on callback.

        The returned state is either the provided state or a newly generated one.
        """
        if state is None:
            import secrets
            state = secrets.token_urlsafe(16)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "repo,read:org",
            "state": state,
        }
        import urllib.parse
        query = urllib.parse.urlencode(params)
        return f"{self.GITHUB_AUTHORIZE_URL}?{query}", state

    def exchange_code_for_token(self, code: str) -> OAuthTokenInfo:
        """
        Exchange an OAuth authorization code for an access token.
        """
        response = requests.post(
            self.GITHUB_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self._client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise ValueError(f"GitHub OAuth error: {data.get('error_description', data['error'])}")

        return OAuthTokenInfo.from_dict(data)

    def save_oauth_token(self, key: str, token_info: OAuthTokenInfo) -> None:
        """Persist an OAuth token to disk."""
        store = _load_token_store()
        store.setdefault("oauth", {})[key] = token_info.to_dict()
        _save_token_store(store)

    def load_oauth_token(self, key: str) -> Optional[OAuthTokenInfo]:
        """Load a stored OAuth token by key (e.g. installation_id or user login)."""
        store = _load_token_store()
        entry = store.get("oauth", {}).get(key)
        if entry:
            return OAuthTokenInfo.from_dict(entry)
        return None

    def exchange_and_store_token(self, code: str, key: str) -> OAuthTokenInfo:
        """
        Exchange code for a token AND persist it atomically.
        """
        token_info = self.exchange_code_for_token(code)
        self.save_oauth_token(key, token_info)
        return token_info

    # ── Installation token generation ─────────────────────────────────────────

    def get_app_jwt(self) -> str:
        """Generate a JWT for GitHub App API authentication."""
        return _generate_jwt(self._app_id, self._private_key)

    def get_installation_token(self, installation_id: str) -> InstallationTokenInfo:
        """
        Generate a new installation token for a GitHub App installation.
        Uses the cached token if still valid.
        """
        store = _load_token_store()
        cached = store.get("installations", {}).get(installation_id)
        if cached:
            info = InstallationTokenInfo.from_dict(cached)
            if not info.is_expired:
                return info

        # Generate fresh token
        jwt_token = self.get_app_jwt()
        response = requests.post(
            f"{self.GITHUB_API_URL}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()
        data = response.json()

        expires_at = data.get("expires_at", "")
        if isinstance(expires_at, str):
            expires_at_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        else:
            expires_at_dt = datetime.now(timezone.utc) + timedelta(hours=1)

        info = InstallationTokenInfo(
            token=data["token"],
            installation_id=installation_id,
            app_id=self._app_id,
            expires_at=expires_at_dt,
        )

        # Cache it
        store.setdefault("installations", {})[installation_id] = info.to_dict()
        _save_token_store(store)

        return info

    def get_installation_token_for_repo(self, owner: str, repo: str) -> InstallationTokenInfo:
        """
        Look up an installation for a repo and return an installation token.
        Raises ValueError if no installation is found.
        """
        # First, find installations for the app
        jwt_token = self._generate_jwt(self._app_id, self._private_key)
        response = requests.get(
            f"{self.GITHUB_API_URL}/app/installations",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()
        installations = response.json()

        # Find matching installation
        for install in installations:
            account = install.get("account", {})
            # Check if this installation has access to the target repo
            target_perms = install.get("permissions", {})
            # We need to check repos separately via installation
            install_id = str(install["id"])

            # Check which repos this installation can access
            repos_resp = requests.get(
                f"{self.GITHUB_API_URL}/installation/repositories",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            if repos_resp.ok:
                repos_data = repos_resp.json()
                repo_logins = [r["full_name"] for r in repos_data.get("repositories", [])]
                if f"{owner}/{repo}" in repo_logins:
                    return self.get_installation_token(install_id)

        raise ValueError(
            f"No GitHub App installation found for repository {owner}/{repo}. "
            "Is the App installed on this repository?"
        )

    # Backward-compat alias
    def _generate_jwt(self, app_id: str, private_key: str) -> str:
        return _generate_jwt(app_id, private_key)
