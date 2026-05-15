# 🩺 repo-pulse

> **GitHub repository health analyzer** — bus factor, issue velocity, commit trends, and a weighted health score. All from your terminal.

```
  ██████████░░░░░░░░░░   52/100  (Fair)

  📦 pallets/flask
  ⭐ 67,412 stars  •  🍴 16,203 forks  •  🐍 Python  •  📜 BSD-3-Clause

  👥 Bus Factor: 3  (LOW risk)
     @davidism    ████████████  41.2%
     @pgjones     ████████      26.7%
     @untitaker   █████         16.1%

  🐛 Issue Velocity: HEALTHY  (74% closure rate)
  📈 Avg commits/month: 23.4
  🚀 Latest release: 3.1.0  (2024-03-14)
```

---

## Why repo-pulse?

Most GitHub tools count stars. **repo-pulse** asks harder questions:

- **Bus factor** — if the top contributor disappeared tomorrow, would the project survive?
- **Issue velocity** — are maintainers winning or drowning?
- **Commit cadence** — is this actively developed or quietly abandoned?
- **Staleness signals** — last release, last commit, open issue ratio

The result is a single **health score (0–100)** backed by real signals, not vanity metrics.

---

## Installation

```bash
# From PyPI (once published)
pip install repo-pulse

# From source
git clone https://github.com/yourusername/repo-pulse
cd repo-pulse
pip install -e .
```

**Requirements:** Python 3.10+

---

## Usage

```bash
# Analyze any public repo
repo-pulse https://github.com/pallets/flask
repo-pulse fastapi/fastapi
repo-pulse psf/requests

# With a GitHub token (raises rate limit from 60 → 5,000 req/hr)
repo-pulse django/django --token ghp_xxxxxxxxxxxx
# or via env var
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
repo-pulse django/django

# Export to JSON
repo-pulse pallets/flask --output json

# Export to Markdown
repo-pulse pallets/flask --output markdown

# Custom output path
repo-pulse pallets/flask --output json --out-file report.json
```

---

## Metrics Explained

### 🩺 Health Score (0–100)

A weighted composite of:

| Signal | Weight | Description |
|--------|--------|-------------|
| License | 10 | Has a recognized open-source license |
| Commit recency | 20 | Days since last push |
| Issue closure rate | 20 | % of issues that get closed |
| Bus factor | 20 | Contributors owning 80% of commits |
| Has releases | 10 | Published GitHub releases |
| Community | 15 | Stars, forks, engagement |
| Documentation | 5 | Description, wiki |

### 👥 Bus Factor

The minimum number of contributors whose combined commits account for 80% of the codebase. A bus factor of 1 means one person going on holiday could stall the whole project.

| Score | Risk |
|-------|------|
| ≥ 3 | 🟢 Low |
| 2 | 🟡 Medium |
| 1 | 🔴 High |

### 🐛 Issue Velocity

Ratio of closed to total issues, plus average days to close a ticket.

| Closure Rate | Status |
|-------------|--------|
| ≥ 70% | 🟢 Healthy |
| 30–70% | 🟡 Fair |
| < 30% | 🔴 Poor |

### 📈 Commit Activity

An ASCII sparkline of monthly commit volume over the past 12 months, plus average commits/month and active author count.

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

### Project Structure

```
repo-pulse/
├── src/
│   └── repo_pulse/
│       ├── __init__.py
│       ├── analyzer.py    # GitHub API client + metric computation
│       ├── display.py     # Rich terminal rendering
│       ├── export.py      # JSON + Markdown export
│       └── cli.py         # Click CLI entry point
├── tests/
│   └── test_analyzer.py
├── pyproject.toml
└── README.md
```

---

## Rate Limits

Without a token, GitHub allows **60 requests/hour**. Most repos fit within this.  
With a [personal access token](https://github.com/settings/tokens), the limit rises to **5,000 requests/hour**.

No special scopes needed — a classic token with no permissions works fine for public repos.

---

## Roadmap

- [ ] `--compare owner/repo1 owner/repo2` — side-by-side health comparison
- [ ] GitHub Actions integration — fail CI if health score drops below threshold
- [ ] Trend tracking — store scores over time and show deltas
- [ ] Private repo support (with token)
- [ ] Web UI / badge generation

---

## Contributing

PRs welcome. Please open an issue first for significant changes.

```bash
git clone https://github.com/yourusername/repo-pulse
cd repo-pulse
pip install -e .
pytest  # make sure everything passes
```

---

## License

[MIT](LICENSE)
