"""Command-line interface for Project Brain Engine."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from brain_engine.validation import ValidationOperationalError, validate_path

app = typer.Typer(name="brain", help="Question-driven context engine for AI-assisted software development.", no_args_is_help=True)
console = Console()


@app.command()
def version() -> None:
    """Show the installed Project Brain Engine version."""
    console.print("[bold cyan]Project Brain Engine[/bold cyan] 0.1.0")


@app.command()
def context(task: Annotated[str, typer.Argument(help="Task that must be understood before implementation.")]) -> None:
    """Analyze a task and identify required project questions."""
    console.print("[bold]Task:[/bold]", task)
    console.print()
    console.print("[yellow]Context analysis is not implemented yet.[/yellow]")


@app.command()
def validate(
    path: Annotated[Path, typer.Argument(help="Markdown file or directory to validate.")] = Path(".brain"),
) -> None:
    """Validate canonical Markdown Brain Items."""
    try:
        result = validate_path(path)
    except ValidationOperationalError as exc:
        console.print(f"[bold red]Operational error:[/bold red] {exc}")
        raise typer.Exit(code=2) from None

    for issue in result.issues:
        color = "red" if issue.severity == "error" else "yellow"
        console.print(f"[{color}][bold]{issue.code}[/bold][/{color}] {issue.path}:{issue.line} {issue.message}")

    table = Table(title="Validation summary")
    table.add_column("Files scanned", justify="right")
    table.add_column("Brain Items found", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Warnings", justify="right")
    table.add_row(str(len(result.files_scanned)), str(len(result.items)), str(result.error_count), str(result.warning_count))
    console.print(table)
    if not result.success:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
