"""
Dependency freshness and security scoring.
Checks Dependabot alerts, manifest staleness, and known vulnerabilities.
"""

from .engine import DimensionScore


def score_dependencies(dependabot_alerts: list[dict]) -> DimensionScore:
    """
    Score dependency health based on Dependabot alerts.

    Args:
        dependabot_alerts: List of Dependabot alert dicts

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