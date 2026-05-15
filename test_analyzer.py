"""
Tests for repo-pulse core analysis logic.
Run with: pytest
"""

import pytest
from repo_pulse.analyzer import RepoAnalyzer, GitHubClient, parse_repo_url


# ── parse_repo_url ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("https://github.com/pallets/flask", ("pallets", "flask")),
    ("https://github.com/pallets/flask.git", ("pallets", "flask")),
    ("github.com/django/django", ("django", "django")),
    ("pallets/flask", ("pallets", "flask")),
    ("git@github.com:psf/requests.git", ("psf", "requests")),
])
def test_parse_repo_url_valid(url, expected):
    assert parse_repo_url(url) == expected


def test_parse_repo_url_invalid():
    with pytest.raises(ValueError):
        parse_repo_url("not-a-repo")


# ── bus factor ──────────────────────────────────────────────────────────────

def make_analyzer():
    return RepoAnalyzer("owner", "repo", GitHubClient())


def test_bus_factor_empty():
    a = make_analyzer()
    result = a.compute_bus_factor([])
    assert result["bus_factor"] == 0
    assert result["risk"] == "unknown"


def test_bus_factor_single_contributor():
    a = make_analyzer()
    contributors = [{"login": "alice", "contributions": 100}]
    result = a.compute_bus_factor(contributors)
    assert result["bus_factor"] == 1
    assert result["risk"] == "high"


def test_bus_factor_distributed():
    a = make_analyzer()
    contributors = [
        {"login": f"user{i}", "contributions": 20}
        for i in range(10)
    ]
    result = a.compute_bus_factor(contributors)
    assert result["bus_factor"] >= 3
    assert result["risk"] == "low"


def test_bus_factor_top_contributors_limit():
    a = make_analyzer()
    contributors = [{"login": f"user{i}", "contributions": 10} for i in range(20)]
    result = a.compute_bus_factor(contributors)
    assert len(result["top_contributors"]) <= 5


# ── issue velocity ──────────────────────────────────────────────────────────

def make_issue(state="open", has_pr=False, days_to_close=None):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    created = (now - timedelta(days=10)).isoformat()
    issue = {
        "created_at": created,
        "closed_at": (now - timedelta(days=10 - days_to_close)).isoformat() if days_to_close else None,
    }
    if has_pr:
        issue["pull_request"] = {}
    return issue


def test_issue_velocity_no_issues():
    a = make_analyzer()
    result = a.compute_issue_velocity([], [])
    assert result["open"] == 0
    assert result["closed"] == 0
    assert result["closure_rate_pct"] == 0


def test_issue_velocity_all_closed():
    a = make_analyzer()
    closed = [make_issue(state="closed", days_to_close=3) for _ in range(10)]
    result = a.compute_issue_velocity([], closed)
    assert result["closure_rate_pct"] == 100.0
    assert result["health"] == "healthy"


def test_issue_velocity_filters_prs():
    a = make_analyzer()
    prs = [make_issue(has_pr=True) for _ in range(5)]
    issues = [make_issue() for _ in range(5)]
    result = a.compute_issue_velocity(issues + prs, [])
    assert result["open"] == 5  # PRs filtered out


# ── health score ────────────────────────────────────────────────────────────

def test_health_score_range():
    a = make_analyzer()
    info = {
        "description": "A great project",
        "has_wiki": True,
        "license": {"spdx_id": "MIT"},
        "stargazers_count": 5000,
        "forks_count": 500,
        "open_issues_count": 20,
    }
    bus = {"bus_factor": 5, "risk": "low"}
    issues = {"closure_rate_pct": 75, "health": "healthy"}
    commits = {"avg_commits_per_month": 20}
    releases = [{"tag_name": "v1.0", "published_at": "2024-01-01T00:00:00Z"}]

    score, notes = a.compute_health_score(info, bus, issues, commits, releases, 5, 30)
    assert 0 <= score <= 100


def test_health_score_penalizes_stale():
    a = make_analyzer()
    info = {"description": None, "has_wiki": False, "license": None,
            "stargazers_count": 0, "forks_count": 0, "open_issues_count": 0}
    bus = {"bus_factor": 1, "risk": "high"}
    issues = {"closure_rate_pct": 5, "health": "poor"}
    commits = {}
    score, notes = a.compute_health_score(info, bus, issues, commits, [], 500, None)
    assert score < 40
    assert any("abandon" in n.lower() or "year" in n.lower() for n in notes)
