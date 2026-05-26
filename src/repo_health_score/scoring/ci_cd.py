"""
CI/CD health scoring.
Analyses GitHub Actions workflow runs for build success, duration, and flakiness.
"""

from typing import Optional
from .engine import DimensionScore


def score_ci_cd(workflow_runs: list[dict]) -> DimensionScore:
    """
    Score CI/CD health based on recent workflow runs.

    Args:
        workflow_runs: List of workflow run dicts from GitHub Actions API

    Returns:
        DimensionScore for CI/CD
    """
    if not workflow_runs:
        return DimensionScore(
            name="ci_cd",
            score=0.0,
            weight=0.20,
            details={"error": "No workflow runs found — CI/CD may not be configured"},
        )

    total_runs = len(workflow_runs)
    successful = sum(1 for r in workflow_runs if r.get("conclusion") == "success")
    failed = sum(1 for r in workflow_runs if r.get("conclusion") == "failure")
    cancelled = sum(1 for r in workflow_runs if r.get("conclusion") == "cancelled")
    skipped = sum(1 for r in workflow_runs if r.get("conclusion") == "skipped")

    # Exclude skipped from the calculation
    active_runs = total_runs - skipped
    if active_runs == 0:
        failure_rate = 0.0
    else:
        failure_rate = failed / active_runs

    success_rate = successful / active_runs if active_runs > 0 else 0.0

    # Score calculation: 100 * success_rate, penalise high failure rates
    score = success_rate * 100

    # Additional penalty for cancelled workflows
    if active_runs > 0:
        cancellation_rate = cancelled / active_runs
        score -= cancellation_rate * 20

    score = max(0.0, min(100.0, score))

    details = {
        "total_runs": total_runs,
        "successful": successful,
        "failed": failed,
        "cancelled": cancelled,
        "skipped": skipped,
        "success_rate": round(success_rate, 3),
        "failure_rate": round(failure_rate, 3),
        "avg_duration_seconds": _avg_duration(workflow_runs),
    }

    return DimensionScore(
        name="ci_cd",
        score=score,
        weight=0.20,
        details=details,
    )


def _avg_duration(runs: list[dict]) -> Optional[float]:
    """Calculate average workflow duration from runs."""
    durations = []
    for run in runs:
        started = run.get("created_at")
        updated = run.get("updated_at")
        if started and updated:
            try:
                from datetime import datetime

                start = datetime.fromisoformat(started.replace("Z", "+00:00"))
                end = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                durations.append((end - start).total_seconds())
            except Exception:
                continue

    return round(sum(durations) / len(durations), 1) if durations else None