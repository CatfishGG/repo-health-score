"""
Tests for Repo Health Score.
"""

import pytest
from repo_health_score.scoring.engine import HealthScorer, RepoHealthReport, DimensionScore
from repo_health_score.scoring import dependencies, ci_cd, pulls, issues


class TestHealthScorer:
    """Tests for the scoring engine."""

    def test_aggregate_all_high_scores(self):
        """All high scores should give an A."""
        scorer = HealthScorer()
        dims = [
            DimensionScore(name="dependencies", score=95.0, weight=0.25),
            DimensionScore(name="ci_cd", score=90.0, weight=0.20),
            DimensionScore(name="pull_requests", score=92.0, weight=0.20),
            DimensionScore(name="issues", score=88.0, weight=0.15),
            DimensionScore(name="community", score=90.0, weight=0.10),
            DimensionScore(name="documentation", score=93.0, weight=0.10),
        ]
        score, letter = scorer.aggregate(dims)
        assert letter == "A"
        assert score >= 90

    def test_aggregate_all_low_scores(self):
        """All low scores should give an F."""
        scorer = HealthScorer()
        dims = [
            DimensionScore(name="dependencies", score=20.0, weight=0.25),
            DimensionScore(name="ci_cd", score=30.0, weight=0.20),
            DimensionScore(name="pull_requests", score=25.0, weight=0.20),
            DimensionScore(name="issues", score=15.0, weight=0.15),
            DimensionScore(name="community", score=20.0, weight=0.10),
            DimensionScore(name="documentation", score=25.0, weight=0.10),
        ]
        score, letter = scorer.aggregate(dims)
        assert letter == "F"
        assert score < 60

    def test_aggregate_mixed_scores(self):
        """Mixed scores should give a B or C."""
        scorer = HealthScorer()
        dims = [
            DimensionScore(name="dependencies", score=80.0, weight=0.25),
            DimensionScore(name="ci_cd", score=75.0, weight=0.20),
            DimensionScore(name="pull_requests", score=60.0, weight=0.20),
            DimensionScore(name="issues", score=85.0, weight=0.15),
            DimensionScore(name="community", score=70.0, weight=0.10),
            DimensionScore(name="documentation", score=78.0, weight=0.10),
        ]
        score, letter = scorer.aggregate(dims)
        assert letter in ["B", "C"]

    def test_aggregate_empty_dims_returns_f(self):
        """Empty dimensions should return F."""
        scorer = HealthScorer()
        score, letter = scorer.aggregate([])
        assert letter == "F"

    def test_recommendations_generated_for_low_scores(self):
        """Low scoring dimensions should generate recommendations."""
        scorer = HealthScorer()
        dims = [
            DimensionScore(name="dependencies", score=40.0, weight=0.25, details={"vulnerability_count": 2}),
            DimensionScore(name="ci_cd", score=30.0, weight=0.20, details={"failure_rate": 0.5}),
            DimensionScore(name="pull_requests", score=50.0, weight=0.20, details={"stale_prs": 3}),
            DimensionScore(name="issues", score=55.0, weight=0.15, details={"no_response_issues": 2}),
        ]
        recs = scorer.generate_recommendations(dims)
        assert len(recs) > 0

    def test_no_recommendations_for_good_scores(self):
        """High scoring dimensions should not generate urgent recommendations."""
        scorer = HealthScorer()
        dims = [
            DimensionScore(name="dependencies", score=90.0, weight=0.25),
            DimensionScore(name="ci_cd", score=88.0, weight=0.20),
            DimensionScore(name="pull_requests", score=92.0, weight=0.20),
            DimensionScore(name="issues", score=85.0, weight=0.15),
        ]
        recs = scorer.generate_recommendations(dims)
        assert len(recs) == 0


class TestDependencyScoring:
    """Tests for dependency scoring."""

    def test_no_alerts_gives_full_score(self):
        """No Dependabot alerts should give a high score."""
        score = dependencies.score_dependencies([])
        assert score.score == 100.0

    def test_critical_vulnerabilities_deduct_significantly(self):
        """Critical vulnerabilities should cause a large deduction."""
        alerts = [
            {"severity": "critical"},
            {"severity": "critical"},
        ]
        score = dependencies.score_dependencies(alerts)
        assert score.score <= 40

    def test_low_severity_vulns_deduct_minimally(self):
        """Low severity vulnerabilities should cause small deductions."""
        alerts = [{"severity": "low"} for _ in range(3)]
        score = dependencies.score_dependencies(alerts)
        assert score.score > 80


class TestPRScoring:
    """Tests for pull request scoring."""

    def test_no_prs_gives_full_score(self):
        """No open PRs should not penalise the score."""
        score = pulls.score_pull_requests([])
        assert score.score == 100.0

    def test_old_prs_deduct_score(self):
        """PRs older than 30 days should reduce the score."""
        from datetime import datetime, timedelta, timezone
        old_date = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat().replace("+00:00", "Z")
        prs = [{"created_at": old_date, "comments": 0, "review_comments": 0}]
        score = pulls.score_pull_requests(prs)
        assert score.score < 100.0


class TestIssueScoring:
    """Tests for issue scoring."""

    def test_no_issues_gives_full_score(self):
        """No open issues should give a perfect score."""
        score = issues.score_issues([])
        assert score.score == 100.0


class TestRepoHealthReport:
    """Tests for the report output."""

    def test_to_dict_returns_expected_structure(self):
        """Report should serialize to dict with all key fields."""
        report = RepoHealthReport(
            owner="test-owner",
            repo="test-repo",
            overall_score=85.5,
            overall_letter="B",
            dimensions=[
                DimensionScore(name="dependencies", score=90.0, weight=0.25),
            ],
            recommendations=["Update outdated deps"],
        )
        d = report.to_dict()
        assert d["owner"] == "test-owner"
        assert d["repo"] == "test-repo"
        assert d["overall_score"] == 85.5
        assert d["overall_letter"] == "B"
        assert len(d["dimensions"]) == 1
        assert len(d["recommendations"]) == 1