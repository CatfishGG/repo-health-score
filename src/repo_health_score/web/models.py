"""
Pydantic models for API request/response schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DimensionResponseModel(BaseModel):
    """A single dimension score in API responses."""
    name: str
    score: float
    weight: float
    letter: str
    details: dict


class ScoreResponse(BaseModel):
    """Full score response for a repo scan."""
    owner: str
    repo: str
    overall_score: float
    overall_letter: str
    dimensions: list[DimensionResponseModel]
    recommendations: list[str]
    scanned_at: datetime


class HistoryEntryResponse(BaseModel):
    """A single entry in score history."""
    id: int
    owner: str
    repo: str
    overall_score: float
    overall_letter: str
    dimensions: list[DimensionResponseModel]
    scanned_at: datetime


class RepoListEntry(BaseModel):
    """A repo entry in the list response."""
    owner: str
    repo: str
    overall_score: float
    overall_letter: str
    scanned_at: Optional[datetime] = None


class ScanRequest(BaseModel):
    """Request body for triggering a scan."""
    token: Optional[str] = None  # GitHub token; can also be set via GITHUB_TOKEN env


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str