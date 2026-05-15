"""
Core analysis engine for repo-pulse.
Fetches GitHub data and computes health metrics.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

import requests

GITHUB_API = "https://api.github.com"


class GitHubClient:
    """Thin wrapper around the GitHub REST API."""

    def __init__(self, token: str | None = None) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            }
        )

    def get(self, path: str, params: dict | None = None) -> Any:
        url = f"{GITHUB_API}{path}"
        resp = self.session.get(url, params=params, timeout=15)
        if resp.status_code == 403:
            raise RateLimitError("GitHub API rate limit hit. Pass a --token to increase limits.")
        if resp.status_code == 404:
            raise RepoNotFoundError(f"Repository not found: {path}")
        resp.raise_for_status()
        return resp.json()

    def get_paginated(self, path: str, params: dict | None = None, max_pages: int = 5) -> list:
        params = params or {}
        params.setdefault("per_page", 100)
        results = []
        for page in range(1, max_pages + 1):
            params["page"] = page
            data = self.get(path, params)
            if not data:
                break
            results.extend(data)
            if len(data) < params["per_page"]:
                break
        return results


class RateLimitError(Exception):
    pass


class RepoNotFoundError(Exception):
    pass


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL or owner/repo string."""
    url = url.strip().rstrip("/")
    patterns = [
        r"github\.com[:/]([^/]+)/([^/\.]+?)(?:\.git)?$",
        r"^([^/]+)/([^/]+)$",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1), m.group(2)
    raise ValueError(f"Cannot parse GitHub repo from: {url!r}")


def days_since(iso_str: str | None) -> int | None:
    if not iso_str:
        return None
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


class RepoAnalyzer:
    def __init__(self, owner: str, repo: str, client: GitHubClient) -> None:
        self.owner = owner
        self.repo = repo
        self.client = client
        self._base = f"/repos/{owner}/{repo}"

    # ------------------------------------------------------------------ #
    #  Data fetchers                                                        #
    # ------------------------------------------------------------------ #

    def fetch_repo_info(self) -> dict:
        return self.client.get(self._base)

    def fetch_commits(self) -> list[dict]:
        return self.client.get_paginated(f"{self._base}/commits", max_pages=5)

    def fetch_issues(self) -> list[dict]:
        open_issues = self.client.get_paginated(
            f"{self._base}/issues", params={"state": "open", "filter": "all"}
        )
        closed_issues = self.client.get_paginated(
            f"{self._base}/issues", params={"state": "closed", "filter": "all"}, max_pages=3
        )
        return open_issues, closed_issues

    def fetch_releases(self) -> list[dict]:
        return self.client.get_paginated(f"{self._base}/releases", max_pages=1)

    def fetch_contributors(self) -> list[dict]:
        try:
            return self.client.get_paginated(f"{self._base}/contributors", max_pages=2)
        except Exception:
            return []

    def fetch_pull_requests(self) -> list[dict]:
        return self.client.get_paginated(
            f"{self._base}/pulls", params={"state": "all"}, max_pages=3
        )

    # ------------------------------------------------------------------ #
    #  Metric computers                                                     #
    # ------------------------------------------------------------------ #

    def compute_bus_factor(self, contributors: list[dict]) -> dict:
        """How many contributors own 80% of commits?"""
        if not contributors:
            return {"bus_factor": 0, "top_contributors": [], "risk": "unknown"}

        total = sum(c["contributions"] for c in contributors)
        sorted_contribs = sorted(contributors, key=lambda c: c["contributions"], reverse=True)

        cumulative = 0
        bus_factor = 0
        for c in sorted_contribs:
            cumulative += c["contributions"]
            bus_factor += 1
            if cumulative / total >= 0.8:
                break

        risk = "low" if bus_factor >= 3 else ("medium" if bus_factor == 2 else "high")
        top = [
            {
                "login": c["login"],
                "contributions": c["contributions"],
                "pct": round(c["contributions"] / total * 100, 1),
            }
            for c in sorted_contribs[:5]
        ]
        return {"bus_factor": bus_factor, "top_contributors": top, "risk": risk}

    def compute_issue_velocity(self, open_issues: list, closed_issues: list) -> dict:
        """Ratio of issues closed vs opened; closure rate trend."""
        total_open = len([i for i in open_issues if "pull_request" not in i])
        total_closed = len([i for i in closed_issues if "pull_request" not in i])
        total = total_open + total_closed

        closure_rate = round(total_closed / total * 100, 1) if total else 0

        # Time-to-close for closed issues (sample)
        close_times = []
        for issue in closed_issues[:50]:
            if "pull_request" in issue:
                continue
            created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            closed = datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00"))
            close_times.append((closed - created).days)

        avg_close_days = round(sum(close_times) / len(close_times), 1) if close_times else None

        health = "healthy" if closure_rate >= 60 else ("fair" if closure_rate >= 30 else "poor")
        return {
            "open": total_open,
            "closed": total_closed,
            "closure_rate_pct": closure_rate,
            "avg_close_days": avg_close_days,
            "health": health,
        }

    def compute_commit_activity(self, commits: list[dict]) -> dict:
        """Monthly commit cadence from recent commits."""
        monthly: dict[str, int] = defaultdict(int)
        authors: Counter = Counter()

        for c in commits:
            date_str = (
                c.get("commit", {}).get("author", {}).get("date")
                or c.get("commit", {}).get("committer", {}).get("date")
            )
            if date_str:
                month = date_str[:7]  # YYYY-MM
                monthly[month] += 1

            login = (c.get("author") or {}).get("login")
            if login:
                authors[login] += 1

        sorted_months = sorted(monthly.items())
        last_6 = sorted_months[-6:] if len(sorted_months) >= 6 else sorted_months
        avg = round(sum(v for _, v in last_6) / len(last_6), 1) if last_6 else 0

        return {
            "total_sampled": len(commits),
            "monthly": dict(sorted_months[-12:]),
            "avg_commits_per_month": avg,
            "active_authors": len(authors),
        }

    def compute_health_score(
        self,
        info: dict,
        bus: dict,
        issues: dict,
        commits: dict,
        releases: list,
        days_since_commit: int | None,
        days_since_release: int | None,
    ) -> tuple[int, list[str]]:
        """Weighted health score out of 100."""
        score = 0
        notes = []

        # 1. Has README (5)
        if info.get("description"):
            score += 3
        # has_wiki / has_pages
        if info.get("has_wiki"):
            score += 2

        # 2. License (10)
        if info.get("license"):
            score += 10
        else:
            notes.append("⚠ No license detected")

        # 3. Recent commit activity (20)
        if days_since_commit is not None:
            if days_since_commit <= 7:
                score += 20
            elif days_since_commit <= 30:
                score += 15
            elif days_since_commit <= 90:
                score += 8
            elif days_since_commit <= 365:
                score += 3
            else:
                notes.append("⚠ Last commit over a year ago — repo may be abandoned")

        # 4. Issue closure rate (20)
        cr = issues["closure_rate_pct"]
        if cr >= 70:
            score += 20
        elif cr >= 50:
            score += 14
        elif cr >= 30:
            score += 7
        else:
            notes.append("⚠ Low issue closure rate — maintainers may be overwhelmed")

        # 5. Bus factor (20)
        bf = bus["bus_factor"]
        if bf >= 5:
            score += 20
        elif bf >= 3:
            score += 14
        elif bf == 2:
            score += 8
        elif bf == 1:
            score += 2
            notes.append("⚠ Bus factor of 1 — project depends on a single contributor")

        # 6. Has releases (10)
        if releases:
            score += 10
            if days_since_release and days_since_release > 365:
                score -= 4
                notes.append("⚠ No release in over a year")
        else:
            notes.append("⚠ No releases published")

        # 7. Community signals (15)
        stars = info.get("stargazers_count", 0)
        forks = info.get("forks_count", 0)
        if stars >= 1000:
            score += 8
        elif stars >= 100:
            score += 5
        elif stars >= 10:
            score += 2
        if forks >= 100:
            score += 4
        elif forks >= 10:
            score += 2
        if info.get("open_issues_count", 0) > 0:
            score += 3  # people are engaged

        return min(score, 100), notes

    # ------------------------------------------------------------------ #
    #  Main entry                                                           #
    # ------------------------------------------------------------------ #

    def analyze(self) -> dict:
        info = self.fetch_repo_info()
        commits = self.fetch_commits()
        open_issues, closed_issues = self.fetch_issues()
        releases = self.fetch_releases()
        contributors = self.fetch_contributors()

        last_commit_date = info.get("pushed_at")
        last_release_date = releases[0]["published_at"] if releases else None

        dsc = days_since(last_commit_date)
        dsr = days_since(last_release_date)

        bus = self.compute_bus_factor(contributors)
        issues = self.compute_issue_velocity(open_issues, closed_issues)
        commit_activity = self.compute_commit_activity(commits)
        score, notes = self.compute_health_score(
            info, bus, issues, commit_activity, releases, dsc, dsr
        )

        return {
            "repo": {
                "full_name": info["full_name"],
                "description": info.get("description") or "No description",
                "url": info["html_url"],
                "language": info.get("language") or "Unknown",
                "stars": info.get("stargazers_count", 0),
                "forks": info.get("forks_count", 0),
                "watchers": info.get("watchers_count", 0),
                "open_issues": info.get("open_issues_count", 0),
                "license": (info.get("license") or {}).get("spdx_id", "None"),
                "created_at": info.get("created_at", "")[:10],
                "days_since_last_commit": dsc,
                "days_since_last_release": dsr,
                "topics": info.get("topics", []),
            },
            "health_score": score,
            "health_notes": notes,
            "bus_factor": bus,
            "issue_velocity": issues,
            "commit_activity": commit_activity,
            "releases": {
                "total": len(releases),
                "latest": releases[0]["tag_name"] if releases else None,
                "latest_date": last_release_date[:10] if last_release_date else None,
            },
        }
