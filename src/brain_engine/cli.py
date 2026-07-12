"""Command-line interface for Project Brain Engine."""

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from brain_engine.context import BrainContentError, ContextBuildError, build_context
from brain_engine.domain import ContextPackage, RequestPackage
from brain_engine.validation import ValidationOperationalError, validate_path

app = typer.Typer(name="brain", help="Question-driven context engine for AI-assisted software development.", no_args_is_help=True)
console = Console()


@app.command()
def version() -> None:
    """Show the installed Project Brain Engine version."""
    console.print("[bold cyan]Project Brain Engine[/bold cyan] 0.1.0")


@app.command()
def context(
    task: Annotated[
        str, typer.Argument(help="Task that must be understood before implementation.")
    ],
    brain_path: Annotated[
        Path, typer.Option("--brain-path", "-b", help="Canonical Brain file or directory.")
    ] = Path(".brain"),
    output_format: Annotated[
        str, typer.Option("--format", "-f", help="Output format: console, json, or yaml.")
    ] = "console",
    max_supporting: Annotated[
        int, typer.Option("--max-supporting", help="Maximum Supporting Items.")
    ] = 5,
    answer: Annotated[
        list[str], typer.Option("--answer", help="Task answer as QUESTION_ID=ANSWER.")
    ] = [],
) -> None:
    """Build deterministic question-driven context for a task."""
    if output_format not in {"console", "json", "yaml"}:
        console.print(f"[bold red]Invalid format:[/bold red] {output_format}. Use console, json, or yaml.")
        raise typer.Exit(code=2)
    if max_supporting < 0:
        console.print("[bold red]Invalid value:[/bold red] --max-supporting must be zero or greater.")
        raise typer.Exit(code=2)
    try:
        request_answers = _parse_answers(answer)
    except ValueError as exc:
        console.print(f"[bold red]Invalid answer:[/bold red] {exc}")
        raise typer.Exit(code=2) from None
    try:
        package = build_context(
            RequestPackage(task, answers=request_answers), brain_path, max_supporting
        )
    except ValidationOperationalError as exc:
        console.print(f"[bold red]Operational error:[/bold red] {exc}")
        raise typer.Exit(code=2) from None
    except BrainContentError as exc:
        console.print(f"[bold red]Invalid Brain:[/bold red] {exc}")
        raise typer.Exit(code=1) from None
    except ContextBuildError as exc:
        console.print(f"[bold red]Context error:[/bold red] {exc}")
        raise typer.Exit(code=1) from None

    if output_format == "json":
        console.print(json.dumps(package.to_dict(), indent=2), markup=False, soft_wrap=True)
    elif output_format == "yaml":
        console.print(yaml.safe_dump(package.to_dict(), sort_keys=False), markup=False, soft_wrap=True)
    else:
        _render_context(package)


def _parse_answers(values: list[str]) -> dict[str, str]:
    answers: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("Expected QUESTION_ID=ANSWER.")
        question_id, answer = (part.strip() for part in value.split("=", 1))
        if not question_id:
            raise ValueError("Question ID must not be empty.")
        if not answer:
            raise ValueError(f"Answer for {question_id!r} must not be empty.")
        if question_id in answers:
            raise ValueError(f"Duplicate Question ID: {question_id}.")
        answers[question_id] = answer
    return answers


def _render_context(package: ContextPackage) -> None:
    classification = package.classification
    execution = package.execution_policy
    console.print(Panel(package.request.task, title="Task"))
    console.print(f"[bold]Intent:[/bold] {classification.intent}")
    console.print(f"[bold]Domains:[/bold] {', '.join(classification.domains) or 'none'}")
    console.print(f"[bold]Risk:[/bold] {classification.risk}")
    console.print(f"[bold]Execution status:[/bold] {execution.status}")
    missing = [item.question_id for item in package.question_resolutions if item.status == "missing"]
    resolved = [item.question_id for item in package.question_resolutions if item.status == "resolved"]
    console.print(f"[bold]Missing Questions:[/bold] {', '.join(missing) or 'none'}")
    console.print(f"[bold]Resolved Questions:[/bold] {', '.join(resolved) or 'none'}")
    request_answers = [
        f"{item.question_id}={item.request_answer}"
        for item in package.question_resolutions
        if item.request_answer is not None
    ]
    console.print(f"[bold]Request answers:[/bold] {', '.join(request_answers) or 'none'}")
    for title, items in (
        ("Critical context", package.critical_items),
        ("Required context", package.required_items),
        ("Supporting context", package.supporting_items),
    ):
        console.print(f"[bold]{title}:[/bold] {', '.join(item.item_id for item in items) or 'none'}")
    console.print(f"[bold]Allowed actions:[/bold] {', '.join(execution.allowed_actions) or 'none'}")
    console.print(f"[bold]Forbidden actions:[/bold] {', '.join(execution.forbidden_actions) or 'none'}")


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
