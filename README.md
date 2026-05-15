# repo-pulse

A command-line tool that analyzes any public GitHub repository and gives you a health report. Built as a Python learning project.

---

## What it does

You point it at any GitHub repo and it pulls data from the GitHub API to answer questions that star counts don't tell you:

- **Bus factor** — how many contributors own the majority of the codebase? If it's just one person, the project is fragile.
- **Issue velocity** — what percentage of issues actually get closed, and how long does it take?
- **Commit activity** — is the repo actively maintained or slowly going quiet?
- **Staleness** — when was the last commit? When was the last release?

It combines these into a single health score out of 100.

---

## Installation

```bash
git clone https://github.com/Mehariscoding/repo-pulse
cd repo-pulse
pip install -e .
```

Requirements: Python 3.10+, and the dependencies `requests`, `rich`, and `click` which install automatically.

---

## Usage

```bash
repo-pulse https://github.com/pallets/flask
repo-pulse django/django
repo-pulse psf/requests --output markdown
```

If you hit the GitHub rate limit (60 requests/hour for unauthenticated users), you can pass a personal access token to raise it to 5,000:

```bash
repo-pulse pallets/flask --token YOUR_TOKEN
# or set it as an environment variable
export GITHUB_TOKEN=YOUR_TOKEN
```

---

## Project structure

```
repo-pulse/
├── analyzer.py       # GitHub API calls and metric computation
├── display.py        # Terminal output using Rich
├── export.py         # Save results as JSON or Markdown
├── cli.py            # Command-line interface using Click
└── test_analyzer.py  # Unit tests for core logic
```

---

## What I learned building this

- How to work with the GitHub REST API including pagination and rate limiting
- Structuring a Python project with separated concerns (fetching, computing, rendering)
- Building CLI tools with Click
- Terminal UI formatting with Rich
- Writing unit tests for data-processing logic

---

The big picture: "I used the GitHub API to pull data about any repo, wrote logic to score it, and displayed it nicely in the terminal."
The four files:

analyzer.py — "This is the brain. It hits the GitHub API, grabs commits, issues, contributors, and calculates things like bus factor and issue closure rate."
display.py — "This takes the results and renders them in the terminal using a library called Rich — the colored boxes, progress bars, all that."
cli.py — "This is the entry point. It uses Click to turn it into a proper command line tool so you can just type python cli.py and a link."
export.py — "This lets you save the report as a JSON or Markdown file if you want to keep it."

One algorithm to highlight: "The bus factor calculation was interesting — I sort contributors by commits, then keep adding them up until I hit 80% of all commits. However many people that took is the bus factor. Flask needed 9 people, my own repo needed 1."

## License

MIT
