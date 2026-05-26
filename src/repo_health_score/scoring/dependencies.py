"""
Dependency freshness and security scoring.
Checks Dependabot alerts, manifest staleness, and known vulnerabilities.
"""

from typing import Optional

from .engine import DimensionScore


def score_dependencies(
    dependabot_alerts: list[dict],
    manifest_info: Optional[dict] = None,
) -> DimensionScore:
    """
    Score dependency health based on Dependabot alerts and manifest info.

    Args:
        dependabot_alerts: List of Dependabot alert dicts
        manifest_info: Optional dict with detected package managers

    Returns:
        DimensionScore for dependencies
    """
    score = 100.0
    details = {}

    # Parse alert counts
    critical_vulns = sum(
        1 for a in dependabot_alerts if a.get("severity") == "critical"
    )
    high_vulns = sum(1 for a in dependabot_alerts if a.get("severity") == "high")
    medium_vulns = sum(1 for a in dependabot_alerts if a.get("severity") == "medium")
    low_vulns = sum(1 for a in dependabot_alerts if a.get("severity") == "low")
    total_vulns = len(dependabot_alerts)

    details["critical_vulnerabilities"] = critical_vulns
    details["high_vulnerabilities"] = high_vulns
    details["medium_vulnerabilities"] = medium_vulns
    details["low_vulnerabilities"] = low_vulns
    details["total_vulnerabilities"] = total_vulns

    # Deduct for vulnerabilities
    # Critical: -30, High: -20, Medium: -10, Low: -5 each
    score -= critical_vulns * 30
    score -= high_vulns * 20
    score -= medium_vulns * 10
    score -= low_vulns * 5

    # Cap at minimum 0
    score = max(0.0, score)

    # Penalise for no lock file (dependency staleness risk)
    if manifest_info:
        has_lock = manifest_info.get("has_lock_file", True)
        if not has_lock:
            score = max(0, score - 10)
            details["no_lock_file"] = True

    details["dependabot_alerts_count"] = len(dependabot_alerts)
    details["outdated_count"] = sum(
        1 for a in dependabot_alerts if a.get("state") == "open"
    )

    return DimensionScore(
        name="dependencies",
        score=score,
        weight=0.25,
        details=details,
    )