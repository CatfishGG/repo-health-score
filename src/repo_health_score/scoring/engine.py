"""
Scoring engine for Repo Health Score.
Aggregates dimension scores into a single letter grade.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta, timezone


@dataclass
class DimensionScore:
    name: str
    score: float  # 0-100
    weight: float  # relative weight
    details: dict = field(default_factory=dict)

    @property
    def letter(self) -> str:
        if self.score >= 90:
            return "A"
        elif self.score >= 80:
            return "B"
        elif self.score >= 70:
            return "C"
        elif self.score >= 60:
            return "D"
        else:
            return "F"


@dataclass
class RepoHealthReport:
    owner: str
    repo: str
    overall_score: float
    overall_letter: str
    dimensions: list[DimensionScore]
    recommendations: list[str]
    scanned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "owner": self.owner,
            "repo": self.repo,
            "overall_score": round(self.overall_score, 2),
            "overall_letter": self.overall_letter,
            "dimensions": [
                {
                    "name": d.name,
                    "score": round(d.score, 2),
                    "weight": d.weight,
                    "letter": d.letter,
                    "details": d.details,
                }
                for d in self.dimensions
            ],
            "recommendations": self.recommendations,
            "scanned_at": self.scanned_at.isoformat(),
        }


class HealthScorer:
    """
    Aggregates dimension scores into a single weighted health score.
    """

    # Default dimension weights (must sum to 1.0)
    DEFAULT_WEIGHTS = {
        "dependencies": 0.25,
        "ci_cd": 0.20,
        "pull_requests": 0.20,
        "issues": 0.15,
        "community": 0.10,
        "documentation": 0.10,
    }

    def __init__(self, custom_weights: Optional[dict] = None):
        if custom_weights:
            self.weights = custom_weights
        else:
            self.weights = self.DEFAULT_WEIGHTS.copy()

    def aggregate(self, dimension_scores: list[DimensionScore]) -> tuple[float, str]:
        """
        Combine dimension scores into a single weighted score.
        Returns (score, letter_grade).
        """
        if not dimension_scores:
            return 0.0, "F"

        total_weighted = 0.0
        total_weight = 0.0

        for dim in dimension_scores:
            weight = self.weights.get(dim.name, 0.0)
            total_weighted += dim.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0, "F"

        final_score = total_weighted / total_weight

        if final_score >= 90:
            letter = "A"
        elif final_score >= 80:
            letter = "B"
        elif final_score >= 70:
            letter = "C"
        elif final_score >= 60:
            letter = "D"
        else:
            letter = "F"

        return final_score, letter

    def generate_recommendations(
        self, dimension_scores: list[DimensionScore]
    ) -> list[str]:
        """
        Generate actionable recommendations based on low-scoring dimensions.
        """
        recommendations = []

        for dim in dimension_scores:
            if dim.score < 60:
                rec = self._recommendation_for(dim)
                if rec:
                    recommendations.append(rec)

        return recommendations

    def _recommendation_for(self, dim: DimensionScore) -> Optional[str]:
        """Build a recommendation string for a low-scoring dimension."""
        details = dim.details

        if dim.name == "dependencies":
            outdated = details.get("outdated_count", 0)
            vuln = details.get("vulnerability_count", 0)
            if vuln > 0:
                return f"Fix {vuln} security vulnerabilities in dependencies immediately"
            if outdated > 0:
                return f"Update {outdated} outdated dependencies"

        elif dim.name == "ci_cd":
            failures = details.get("failure_rate", 0)
            if failures > 0.3:
                return f"CI/CD has {int(failures*100)}% failure rate — fix failing workflows"

        elif dim.name == "pull_requests":
            stale = details.get("stale_prs", 0)
            avg_age = details.get("avg_age_days", 0)
            if stale > 0:
                return f"Close or address {stale} stale pull requests"
            if avg_age > 30:
                return f"Average PR age is {avg_age} days — consider timely reviews"

        elif dim.name == "issues":
            no_response = details.get("no_response_issues", 0)
            avg_age = details.get("avg_age_days", 0)
            if no_response > 0:
                return f"Respond to {no_response} issues with no maintainer response"
            if avg_age > 60:
                return f"Average issue age is {avg_age} days — triage or close old issues"

        elif dim.name == "community":
            if details.get("contributors", 0) == 0:
                return "No contributors detected — consider adding contribution guidelines"

        elif dim.name == "documentation":
            if not details.get("has_readme"):
                return "Add a README.md to improve repo discoverability"
            if details.get("last_doc_update_days", 0) > 180:
                return "Documentation is outdated — consider updating README/docs"

        return None