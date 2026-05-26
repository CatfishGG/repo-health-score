"""
FastAPI application for Repo Health Score web server.
"""

import os
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, store_score, get_history, get_latest_score, get_all_repos
from .models import (
    ScoreResponse,
    HistoryEntryResponse,
    HealthResponse,
    DimensionResponseModel,
    RepoListEntry,
)
from .badge import router as badge_router
from ..scoring.scanner import scan_repo, ScannerConfig

# Version
__version__ = "0.1.0"

# Create app
app = FastAPI(
    title="Repo Health Score API",
    description="A unified health scoring API for GitHub repositories.",
    version=__version__,
)

# Add CORS middleware — restrict origins in production via ALLOWED_ORIGINS env var
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "").split(",")
if not allowed_origins or allowed_origins == [""]:
    allowed_origins = ["http://localhost:3000", "http://localhost:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include badge routes
app.include_router(badge_router)


@app.on_event("startup")
def startup_event():
    """Initialize the database on startup."""
    init_db()


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok", version=__version__)


@app.get("/repos", response_model=list[RepoListEntry], tags=["repos"])
def list_repos(limit: int = Query(100, ge=1, le=1000, description="Max repos to return")):
    """
    List all repositories that have at least one stored score, with their most recent score.
    Sorted by score ascending (worst repos first).
    """
    rows = get_all_repos(limit=limit)
    return [
        RepoListEntry(
            owner=row["owner"],
            repo=row["repo"],
            overall_score=row["overall_score"],
            overall_letter=row["overall_letter"],
            scanned_at=datetime.fromisoformat(row["scanned_at"]) if row.get("scanned_at") else None,
        )
        for row in rows
    ]


def _get_token(token: Optional[str] = None) -> str:
    """Resolve the GitHub token from request or environment."""
    if token:
        return token
    env_token = os.environ.get("GITHUB_TOKEN")
    if not env_token:
        raise HTTPException(
            status_code=401,
            detail="GitHub token not provided. Set GITHUB_TOKEN env var or pass token in request."
        )
    return env_token


@app.get("/repos/{owner}/{repo}/score", response_model=ScoreResponse, tags=["scores"])
def get_score(
    owner: str,
    repo: str,
    token: Optional[str] = None,
    store: bool = Query(True, description="Whether to store the score in history"),
):
    """
    Get the current health score for a repository (scans on demand).
    Optionally stores the result in score history.
    """
    github_token = _get_token(token)
    config = ScannerConfig()
    report = scan_repo(owner, repo, github_token, config)

    if store:
        dimensions_json = json.dumps([d.to_dict() for d in report.dimensions])
        store_score(
            owner=report.owner,
            repo=report.repo,
            overall_score=report.overall_score,
            overall_letter=report.overall_letter,
            dimensions_json=dimensions_json,
            scanned_at=report.scanned_at.isoformat(),
        )

    return ScoreResponse(
        owner=report.owner,
        repo=report.repo,
        overall_score=report.overall_score,
        overall_letter=report.overall_letter,
        dimensions=[
            DimensionResponseModel(
                name=d.name,
                score=d.score,
                weight=d.weight,
                letter=d.letter,
                details=d.details,
            )
            for d in report.dimensions
        ],
        recommendations=report.recommendations,
        scanned_at=report.scanned_at,
    )


@app.get("/repos/{owner}/{repo}/history", response_model=list[HistoryEntryResponse], tags=["scores"])
def get_repo_history(
    owner: str,
    repo: str,
    days: Optional[int] = Query(30, description="Number of days of history to retrieve"),
):
    """
    Get score history for a repository.
    """
    rows = get_history(owner, repo, days=days if days > 0 else None)
    return [
        HistoryEntryResponse(
            id=row["id"],
            owner=row["owner"],
            repo=row["repo"],
            overall_score=row["overall_score"],
            overall_letter=row["overall_letter"],
            dimensions_json=row["dimensions_json"],
            scanned_at=datetime.fromisoformat(row["scanned_at"]),
        )
        for row in rows
    ]


@app.get("/repos/{owner}/{repo}/history/latest", response_model=ScoreResponse, tags=["scores"])
def get_latest(owner: str, repo: str):
    """
    Get the most recent score for a repository.
    Returns 404 if no history exists.
    """
    row = get_latest_score(owner, repo)
    if not row:
        raise HTTPException(status_code=404, detail="No score history found for this repository")

    dimensions = json.loads(row["dimensions_json"])
    return ScoreResponse(
        owner=row["owner"],
        repo=row["repo"],
        overall_score=row["overall_score"],
        overall_letter=row["overall_letter"],
        dimensions=[
            DimensionResponseModel(
                name=d["name"],
                score=d["score"],
                weight=d["weight"],
                letter=d["letter"],
                details=d.get("details", {}),
            )
            for d in dimensions
        ],
        recommendations=[],  # Not stored in history
        scanned_at=datetime.fromisoformat(row["scanned_at"]),
    )


@app.post("/repos/{owner}/{repo}/scan", response_model=ScoreResponse, tags=["scores"])
def trigger_scan(
    owner: str,
    repo: str,
    token: Optional[str] = None,
):
    """
    Trigger a new scan for a repository and store the result in history.
    """
    github_token = _get_token(token)
    config = ScannerConfig()
    report = scan_repo(owner, repo, github_token, config)

    dimensions_json = json.dumps([d.to_dict() for d in report.dimensions])
    store_score(
        owner=report.owner,
        repo=report.repo,
        overall_score=report.overall_score,
        overall_letter=report.overall_letter,
        dimensions_json=dimensions_json,
        scanned_at=report.scanned_at.isoformat(),
    )

    return ScoreResponse(
        owner=report.owner,
        repo=report.repo,
        overall_score=report.overall_score,
        overall_letter=report.overall_letter,
        dimensions=[
            DimensionResponseModel(
                name=d.name,
                score=d.score,
                weight=d.weight,
                letter=d.letter,
                details=d.details,
            )
            for d in report.dimensions
        ],
        recommendations=report.recommendations,
        scanned_at=report.scanned_at,
    )