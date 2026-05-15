"""
Terminal display using Rich.
Renders all analysis results in a beautiful CLI layout.
"""

from __future__ import annotations

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()


def score_color(score: int) -> str:
    if score >= 80:
        return "bright_green"
    if score >= 60:
        return "yellow"
    if score >= 40:
        return "orange3"
    return "red"


def score_label(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Fair"
    return "Poor"


def render_score_gauge(score: int) -> Panel:
    color = score_color(score)
    label = score_label(score)
    filled = score // 5
    bar = "█" * filled + "░" * (20 - filled)

    text = Text()
    text.append(f"  {bar}  ", style=color)
    text.append(f" {score}/100  ", style=f"bold {color}")
    text.append(f"({label})", style=f"dim {color}")

    return Panel(
        text,
        title="[bold white]🩺 Health Score[/bold white]",
        border_style=color,
        padding=(0, 1),
    )


def render_repo_info(repo: dict) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()

    rows = [
        ("📦 Repo", f"[bold cyan]{repo['full_name']}[/bold cyan]"),
        ("📝 Description", repo["description"]),
        ("🔤 Language", f"[yellow]{repo['language']}[/yellow]"),
        ("⭐ Stars", f"[bold]{repo['stars']:,}[/bold]"),
        ("🍴 Forks", str(repo["forks"])),
        ("👁  Watchers", str(repo["watchers"])),
        ("🐛 Open Issues", str(repo["open_issues"])),
        ("📜 License", f"[green]{repo['license']}[/green]"),
        ("📅 Created", repo["created_at"]),
        (
            "🕐 Last Commit",
            f"{repo['days_since_last_commit']}d ago"
            if repo["days_since_last_commit"] is not None
            else "unknown",
        ),
    ]

    if repo["topics"]:
        rows.append(("🏷  Topics", "  ".join(f"[blue]{t}[/blue]" for t in repo["topics"][:8])))

    for label, value in rows:
        table.add_row(label, value)

    return Panel(table, title="[bold white]Repository Overview[/bold white]", border_style="cyan")


def render_bus_factor(bus: dict) -> Panel:
    risk_colors = {"low": "green", "medium": "yellow", "high": "red", "unknown": "dim"}
    risk = bus["risk"]
    color = risk_colors.get(risk, "dim")

    text = Text()
    text.append(f"  Bus Factor: ", style="dim")
    text.append(f"{bus['bus_factor']}", style=f"bold {color} underline")
    text.append(f"  ({risk.upper()} risk)\n\n", style=color)

    if bus["top_contributors"]:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
        table.add_column("Contributor")
        table.add_column("Commits", justify="right")
        table.add_column("Share", justify="right")

        for c in bus["top_contributors"]:
            bar = "▓" * int(c["pct"] / 5)
            table.add_row(
                f"[cyan]@{c['login']}[/cyan]",
                str(c["contributions"]),
                f"[{color}]{c['pct']}%[/{color}] {bar}",
            )
        return Panel(
            text.__add__(Text.from_markup(str(table))),
            title="[bold white]👥 Bus Factor[/bold white]",
            border_style=color,
        )

    # fallback if no table
    return Panel(text, title="[bold white]👥 Bus Factor[/bold white]", border_style=color)


def render_bus_factor_table(bus: dict) -> Table:
    risk_colors = {"low": "green", "medium": "yellow", "high": "red", "unknown": "dim"}
    risk = bus["risk"]
    color = risk_colors.get(risk, "dim")

    table = Table(
        title=f"👥 Bus Factor: [bold {color}]{bus['bus_factor']}[/bold {color}]  ({risk.upper()} risk)",
        box=box.ROUNDED,
        border_style=color,
        show_header=True,
        header_style="bold",
    )
    table.add_column("Contributor", style="cyan")
    table.add_column("Commits", justify="right")
    table.add_column("Share", justify="right")
    table.add_column("", no_wrap=True)

    for c in bus["top_contributors"]:
        bar_len = max(1, int(c["pct"] / 4))
        table.add_row(
            f"@{c['login']}",
            str(c["contributions"]),
            f"{c['pct']}%",
            f"[{color}]{'█' * bar_len}[/{color}]",
        )
    return table


def render_issue_velocity(issues: dict) -> Table:
    health_colors = {"healthy": "green", "fair": "yellow", "poor": "red"}
    h = issues["health"]
    color = health_colors.get(h, "dim")

    table = Table(
        title="🐛 Issue Velocity",
        box=box.ROUNDED,
        border_style=color,
        show_header=False,
    )
    table.add_column(style="dim", min_width=20)
    table.add_column()

    closure_bar_len = max(1, int(issues["closure_rate_pct"] / 5))
    closure_bar = f"[{color}]{'█' * closure_bar_len}[/{color}]"

    table.add_row("Open Issues", str(issues["open"]))
    table.add_row("Closed Issues", str(issues["closed"]))
    table.add_row(
        "Closure Rate",
        f"[bold {color}]{issues['closure_rate_pct']}%[/bold {color}] {closure_bar}",
    )
    table.add_row("Status", f"[{color}]{h.upper()}[/{color}]")
    if issues["avg_close_days"] is not None:
        table.add_row("Avg Days to Close", f"{issues['avg_close_days']} days")

    return table


def render_commit_sparkline(monthly: dict) -> str:
    """ASCII sparkline of monthly commit activity."""
    if not monthly:
        return "(no data)"
    values = list(monthly.values())
    max_v = max(values) if values else 1
    blocks = " ▁▂▃▄▅▆▇█"
    spark = ""
    for v in values[-12:]:
        idx = int(v / max_v * (len(blocks) - 1))
        spark += blocks[idx]
    return spark


def render_commit_activity(activity: dict) -> Panel:
    spark = render_commit_sparkline(activity["monthly"])
    months = list(activity["monthly"].keys())
    start = months[0] if months else "?"
    end = months[-1] if months else "?"

    text = Text()
    text.append(f"\n  {spark}\n", style="cyan")
    text.append(f"  {start} → {end}\n\n", style="dim")
    text.append(f"  Avg commits/month: ", style="dim")
    text.append(f"{activity['avg_commits_per_month']}\n", style="bold")
    text.append(f"  Active authors (sample): ", style="dim")
    text.append(f"{activity['active_authors']}\n", style="bold")
    text.append(f"  Commits sampled: ", style="dim")
    text.append(f"{activity['total_sampled']}\n", style="dim")

    return Panel(
        text,
        title="[bold white]📈 Commit Activity[/bold white]",
        border_style="cyan",
    )


def render_releases(releases: dict) -> Panel:
    text = Text()
    if releases["total"] == 0:
        text.append("\n  No releases published.\n", style="red dim")
    else:
        text.append(f"\n  Total releases: ", style="dim")
        text.append(f"{releases['total']}\n", style="bold")
        text.append(f"  Latest: ", style="dim")
        text.append(f"{releases['latest']}  ", style="bold green")
        text.append(f"({releases['latest_date']})\n", style="dim")

    return Panel(text, title="[bold white]🚀 Releases[/bold white]", border_style="magenta")


def render_health_notes(notes: list[str]) -> Panel | None:
    if not notes:
        return None
    text = Text()
    for note in notes:
        text.append(f"  {note}\n", style="yellow")
    return Panel(text, title="[bold white]⚡ Warnings[/bold white]", border_style="yellow")


def display_report(data: dict) -> None:
    console.print()
    console.print(Rule("[bold cyan]repo-pulse[/bold cyan]  •  GitHub Repository Health Analyzer"))
    console.print()

    # Score + overview side by side
    console.print(render_score_gauge(data["health_score"]))
    console.print()
    console.print(render_repo_info(data["repo"]))
    console.print()

    # Bus factor + issue velocity
    console.print(render_bus_factor_table(data["bus_factor"]))
    console.print()
    console.print(render_issue_velocity(data["issue_velocity"]))
    console.print()

    # Commit activity + releases
    console.print(render_commit_activity(data["commit_activity"]))
    console.print()
    console.print(render_releases(data["releases"]))

    # Warnings
    notes_panel = render_health_notes(data["health_notes"])
    if notes_panel:
        console.print()
        console.print(notes_panel)

    console.print()
    console.print(Rule(style="dim"))
    console.print()


def make_spinner(msg: str) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[cyan]{task.description}"),
        transient=True,
        console=console,
    )
