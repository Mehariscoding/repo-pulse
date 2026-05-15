"""
repo-pulse CLI entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from repo_pulse.analyzer import (
    GitHubClient,
    RateLimitError,
    RepoAnalyzer,
    RepoNotFoundError,
    parse_repo_url,
)
from repo_pulse.display import display_report
from repo_pulse.export import export_json, export_markdown

console = Console()
err_console = Console(stderr=True)


@click.command()
@click.argument("repo_url")
@click.option(
    "--token",
    "-t",
    envvar="GITHUB_TOKEN",
    default=None,
    help="GitHub personal access token (or set GITHUB_TOKEN env var). "
    "Increases rate limit from 60 to 5,000 req/hr.",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "markdown", "md"]),
    default=None,
    help="Export format. Saves to repo-pulse-<repo>.json or .md",
)
@click.option(
    "--out-file",
    "-f",
    default=None,
    help="Custom output file path.",
)
def main(repo_url: str, token: str | None, output: str | None, out_file: str | None) -> None:
    """
    \b
    repo-pulse — GitHub Repository Health Analyzer
    ───────────────────────────────────────────────
    Analyze any public GitHub repository and get a comprehensive
    health report: bus factor, issue velocity, commit trends, and more.

    \b
    Examples:
      repo-pulse https://github.com/pallets/flask
      repo-pulse fastapi/fastapi
      repo-pulse django/django --output markdown
      repo-pulse psf/requests --token ghp_xxxx
    """
    try:
        owner, repo = parse_repo_url(repo_url)
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    client = GitHubClient(token=token)
    analyzer = RepoAnalyzer(owner, repo, client)

    steps = [
        ("Fetching repository info…", None),
        ("Analyzing commits…", None),
        ("Scanning issues…", None),
        ("Counting contributors…", None),
        ("Checking releases…", None),
        ("Computing health score…", None),
    ]

    console.print()
    console.print(
        f"  [bold cyan]repo-pulse[/bold cyan]  analyzing "
        f"[bold]{owner}/{repo}[/bold]  …"
    )
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("  [cyan]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("Fetching data…", total=None)

        try:
            progress.update(task, description="Fetching repository info…")
            data = analyzer.analyze()
        except RateLimitError as e:
            err_console.print(f"\n[red]Rate limit:[/red] {e}")
            sys.exit(1)
        except RepoNotFoundError as e:
            err_console.print(f"\n[red]Not found:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            err_console.print(f"\n[red]Error:[/red] {e}")
            if "--debug" in sys.argv:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    display_report(data)

    # Export if requested
    if output or out_file:
        fmt = output or "json"
        slug = f"{owner}-{repo}"
        if out_file:
            out_path = Path(out_file)
        elif fmt in ("markdown", "md"):
            out_path = Path(f"repo-pulse-{slug}.md")
        else:
            out_path = Path(f"repo-pulse-{slug}.json")

        if fmt in ("markdown", "md"):
            export_markdown(data, out_path)
        else:
            export_json(data, out_path)

        console.print(f"  [green]✓[/green] Report saved to [bold]{out_path}[/bold]\n")


if __name__ == "__main__":
    main()
