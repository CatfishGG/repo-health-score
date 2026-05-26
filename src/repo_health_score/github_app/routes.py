"""
Web routes for the GitHub App server.

Provides:
- GET /health — liveness check
- GET /oauth/callback — GitHub OAuth redirect handler
- POST /webhook — GitHub App webhook event receiver
- GET /install — redirect to GitHub App installation flow
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse


# ─── Router ───────────────────────────────────────────────────────────────────

router = APIRouter()

# In-memory state store for CSRF protection (per-server, single-process)
# For production, use a shared Redis store or signed cookies
_oauth_state_store: dict[str, float] = {}
_STATE_TTL_SECONDS = 600


def _generate_state() -> str:
    """Generate a cryptographically random OAuth state parameter."""
    state = secrets.token_urlsafe(24)
    import time
    _oauth_state_store[state] = time.monotonic()
    return state


def _validate_state(state: str) -> bool:
    """Validate and consume a state parameter (single-use)."""
    import time
    if state not in _oauth_state_store:
        return False
    expiry = _oauth_state_store.pop(state)
    if time.monotonic() - expiry > _STATE_TTL_SECONDS:
        return False
    return True


def _authenticator():
    """Lazy import to avoid circular deps and ensure env is ready."""
    from repo_health_score.github_app.auth import GitHubAppAuthenticator
    return GitHubAppAuthenticator()


# ─── OAuth callback ───────────────────────────────────────────────────────────

@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from GitHub"),
    state: str = Query("", description="CSRF state token"),
):
    """
    Handle the OAuth callback from GitHub.
    Exchanges the code for an access token and redirects to a success page.
    """
    # Validate CSRF state to prevent cross-site request forgery
    if not _validate_state(state):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state. Please try installing again.",
        )

    auth = _authenticator()

    try:
        auth.exchange_and_store_token(code, key="default")
    except Exception as exc:
        return HTMLResponse(
            f"<html><body><h1>OAuth Error</h1><p>{exc}</p></body></html>",
            status_code=400,
        )

    html = """
    <!DOCTYPE html>
    <html>
    <head><title>GitHub App Connected</title></head>
    <body>
    <h1>Connected!</h1>
    <p>Your GitHub account has been successfully linked.</p>
    <p>Access token acquired. You can now close this window and use the CLI.</p>
    <script>
        // Attempt to signalopener tab / parent
        if (window.opener) {
            window.opener.postMessage("github_app_connected", "*");
            window.close();
        }
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


# ─── Install redirect ─────────────────────────────────────────────────────────

@router.get("/install")
async def install_app():
    """
    Redirect the user to GitHub to authorize / install the GitHub App.
    """
    auth = _authenticator()
    state = _generate_state()
    url, _ = auth.get_authorization_url(state=state)
    return RedirectResponse(url, status_code=302)


# ─── Webhook ──────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def webhook(request: Request):
    """
    Receive GitHub App webhook events.
    Validates the signature and dispatches to handlers.
    """
    webhook_secret = os.environ.get("GITHUB_APP_WEBHOOK_SECRET")

    body = await request.body()
    headers = dict(request.headers)

    # Reject webhooks without a secret configured (webhook_secret == "" means unset)
    if webhook_secret is None:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_APP_WEBHOOK_SECRET is not configured. "
                    "Set it in GitHub App settings to secure webhook delivery.",
        )

    # Validate signature
    signature = headers.get("x-hub-signature-256", "")
    expected = "sha256=" + hmac.new(
        webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = headers.get("x-github-event", "unknown")
    delivery_id = headers.get("x-github-delivery", "")

    payload = json.loads(body) if body else {}

    # Handle known event types
    if event == "installation" or event == "installation_repositories":
        return await _handle_installation_event(payload, auth=_authenticator())

    if event == "push":
        return await _handle_push_event(payload)

    if event == "pull_request":
        return await _handle_pull_request_event(payload)

    # Default: acknowledge receipt
    return JSONResponse({"ok": True, "event": event, "delivery_id": delivery_id})


async def _handle_installation_event(payload: dict, auth) -> JSONResponse:
    """Handle installation / installation_repositories events."""
    action = payload.get("action", "")
    installation_id = str(payload.get("installation", {}).get("id", ""))
    account_login = payload.get("account", {}).get("login", "unknown")

    if action in ("created", "new_permissions_accepted"):
        # App was installed or new permissions granted — acknowledge.
        # Token caching happens lazily on first actual API call,
        # no need to pre-generate here.
        return JSONResponse({
            "ok": True,
            "message": f"Installation {installation_id} for {account_login} activated.",
            "installation_id": installation_id,
            "account": account_login,
        })

    if action in ("deleted", "suspend"):
        # App was uninstalled
        return JSONResponse({
            "ok": True,
            "message": f"Installation {installation_id} removed.",
        })

    return JSONResponse({"ok": True, "action": action})


async def _handle_push_event(payload: dict) -> JSONResponse:
    """Handle push events (placeholder for future scoring triggers)."""
    repo = payload.get("repository", {}).get("full_name", "unknown")
    return JSONResponse({"ok": True, "message": f"Push event recorded for {repo}"})


async def _handle_pull_request_event(payload: dict) -> JSONResponse:
    """Handle PR events (placeholder for future scoring triggers)."""
    repo = payload.get("repository", {}).get("full_name", "unknown")
    pr_action = payload.get("action", "")
    pr_number = payload.get("pull_request", {}).get("number", 0)
    return JSONResponse({
        "ok": True,
        "message": f"PR #{pr_number} {pr_action} recorded for {repo}",
    })


# ─── Health check ─────────────────────────────────────────────────────────────

health_router = APIRouter()


@health_router.get("/health")
async def health():
    """Liveness check — confirms the server is running."""
    return {"status": "ok"}


# ─── FastAPI app builder ──────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    Includes:
    - CORS for local dev
    - Routes registered at root level
    - JSON exception handlers
    """
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="Repo Health Score — GitHub App",
        description="GitHub App server handling OAuth, webhooks, and installation tokens.",
        version="0.1.0",
    )

    allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8484").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-GitHub-Event", "X-GitHub-Delivery", "X-Hub-Signature-256"],
    )

    # Mount routes at root
    app.include_router(router, tags=["GitHub App"])
    app.include_router(health_router, tags=["Health"])

    return app
