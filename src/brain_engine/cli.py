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
from brain_engine.discovery import DiscoveryService
from brain_engine.validation import ValidationOperationalError, validate_path
from brain_engine import __version__
from brain_engine.application.launcher import run_app
from brain_engine.experiment import ExperimentError, ExperimentService
from brain_engine.initialization import BrainExistsError, InitializationRequest, initialize_brain

app = typer.Typer(name="brain", help="Question-driven context engine for AI-assisted software development.", no_args_is_help=True)
experiment_app = typer.Typer(name="experiment", help="Controlled local A/B experiments.", no_args_is_help=True)
app.add_typer(experiment_app, name="experiment")
console = Console()


@app.command("scan")
def scan_command(
    repository: Annotated[Path, typer.Argument(help="Local Git repository to analyze.")],
    data_dir: Annotated[
        Path | None, typer.Option("--data-dir", help="Application-managed data directory.")
    ] = None,
) -> None:
    """Create an immutable, deterministic project discovery revision."""
    target = (data_dir or Path.home() / ".project-brain-engine").resolve()
    try:
        report = DiscoveryService(target).scan(repository)
    except (OSError, RuntimeError, ValueError) as exc:
        console.print(f"[bold red]Discovery error:[/bold red] {exc}")
        raise typer.Exit(1) from None
    metadata = report["metadata"]
    console.print(f"Project ID: {metadata['project_id']}")
    console.print(f"Repository SHA: {metadata['repository_sha']}")
    console.print(f"Revision: {metadata['revision']}")
    console.print(
        "Counts: "
        f"findings={len(report['findings'])}, proposals={len(report['proposals'])}, "
        f"questions={len(report['questions'])}, conflicts={len(report['conflicts'])}"
    )
    console.print(f"Report: {report['report_path']}")
    for warning in report["warnings"]:
        console.print(f"[yellow]Partial scan:[/yellow] {warning}")


@app.command()
def version() -> None:
    """Show the installed Project Brain Engine version."""
    console.print(f"[bold cyan]Project Brain Engine[/bold cyan] {__version__}")


@app.command("app")
def application(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 8765,
    no_open: Annotated[bool, typer.Option("--no-open")] = False,
    data_dir: Annotated[Path | None, typer.Option("--data-dir")] = None,
) -> None:
    """Start the local browser application."""
    run_app(host, port, not no_open, data_dir)


@app.command("init")
def init_command(
    path: Annotated[Path, typer.Option("--path")] = Path("."),
    non_interactive: Annotated[bool, typer.Option("--non-interactive")] = False,
    project_name: Annotated[str | None, typer.Option("--project-name")] = None,
    project_purpose: Annotated[str | None, typer.Option("--project-purpose")] = None,
    primary_technology: Annotated[str | None, typer.Option("--primary-technology")] = None,
    language: Annotated[str | None, typer.Option("--language")] = None,
) -> None:
    """Initialize proposed, owner-reviewed Project Brain knowledge."""
    values = (project_name, project_purpose, primary_technology, language)
    if non_interactive and any(value is None for value in values):
        console.print("[bold red]Missing values:[/bold red] non-interactive mode requires all project fields.")
        raise typer.Exit(2)
    name = project_name or typer.prompt("Project display name")
    purpose = project_purpose or typer.prompt("Project purpose")
    technology = primary_technology or typer.prompt("Primary technology")
    selected_language = language or typer.prompt("Project language", default="en")
    try:
        result = initialize_brain(InitializationRequest(path, name, purpose, technology, selected_language))
    except BrainExistsError as exc:
        console.print(f"[bold red]Initialization refused:[/bold red] {exc}")
        raise typer.Exit(1) from None
    console.print(f"Created {len(result.created_files)} files in {result.brain_path}")
    console.print(f"Proposed Items: {result.proposed_item_count}; validation errors: {result.validation_errors}")
    console.print("[yellow]No project knowledge was automatically approved.[/yellow]")
    console.print("Next: review Items, approve trusted knowledge explicitly, then run brain validate.")


@experiment_app.command("init")
def experiment_init(
    repository: Annotated[Path, typer.Option("--repository", "-r")],
    output: Annotated[Path, typer.Option("--output", "-o")],
    task_file: Annotated[Path, typer.Option("--task-file")],
    ground_truth_file: Annotated[Path, typer.Option("--ground-truth-file")],
    brain_path: Annotated[Path, typer.Option("--brain-path", "-b")],
    privacy: Annotated[str, typer.Option("--privacy")] = "private",
    allow_existing_brain: Annotated[bool, typer.Option("--allow-existing-brain")] = False,
) -> None:
    """Create an isolated controlled experiment."""
    try:
        root = ExperimentService().initialize(repository, output, task_file.read_text(encoding="utf-8"), ground_truth_file.read_text(encoding="utf-8"), brain_path, privacy=privacy, allow_existing_brain=allow_existing_brain)
    except (ExperimentError, OSError, UnicodeError) as exc:
        console.print(f"[bold red]Experiment error:[/bold red] {exc}")
        raise typer.Exit(1) from None
    console.print(f"Experiment created: {root}")
    console.print("Treatment mapping is private. Normal status uses neutral result names.")


@experiment_app.command("status")
def experiment_status(root: Annotated[Path, typer.Argument()]) -> None:
    """Display neutral, read-only experiment status."""
    try:
        status, consistent = ExperimentService().status(root)
    except Exception as exc:
        console.print(f"[bold red]Experiment error:[/bold red] {exc}")
        raise typer.Exit(2) from None
    console.print(yaml.safe_dump(status, sort_keys=False, allow_unicode=True), markup=False)
    if not consistent:
        raise typer.Exit(1)


@experiment_app.command("context")
def experiment_context(root: Annotated[Path, typer.Argument()]) -> None:
    """Show the frozen Context Package without regenerating it."""
    state = __import__("brain_engine.experiment.storage", fromlist=["load_state"]).load_state(root)
    console.print((root / state["context_package"]["path"]).read_text(encoding="utf-8"), markup=False)


@experiment_app.command("start")
def experiment_start(root: Annotated[Path, typer.Argument()], result: Annotated[str, typer.Option("--result")]) -> None:
    ExperimentService().start_run(root, result)
    console.print(f"Started {result}")


@experiment_app.command("finish")
def experiment_finish(
    root: Annotated[Path, typer.Argument()], result: Annotated[str, typer.Option("--result")],
    final_report: Annotated[Path, typer.Option("--final-report")],
    permission_prompts: Annotated[int, typer.Option("--permission-prompts")] = 0,
    setup_prompts: Annotated[int, typer.Option("--setup-prompts")] = 0,
    task_permission_prompts: Annotated[
        int | None, typer.Option("--task-permission-prompts")
    ] = None,
    clarification_questions: Annotated[int, typer.Option("--clarification-questions")] = 0,
    corrective_iterations: Annotated[int, typer.Option("--corrective-iterations")] = 0,
) -> None:
    metadata = {
        "final_report": final_report.read_text(encoding="utf-8"),
        "permission_prompts": permission_prompts,
        "setup_prompts": setup_prompts,
        "task_permission_prompts": (
            permission_prompts if task_permission_prompts is None else task_permission_prompts
        ),
        "clarification_questions": clarification_questions,
        "corrective_iterations": corrective_iterations,
    }
    ExperimentService().finish_run(root, result, metadata)
    console.print(f"Finished {result}")


@experiment_app.command("capture")
def experiment_capture(root: Annotated[Path, typer.Argument()], result: Annotated[str, typer.Option("--result")]) -> None:
    console.print(f"Evidence captured: {ExperimentService().capture(root, result)}")


@experiment_app.command("finalize")
def experiment_finalize(root: Annotated[Path, typer.Argument()]) -> None:
    try:
        console.print(f"Integrity manifest: {ExperimentService().finalize(root)}")
    except ExperimentError as exc:
        console.print(f"[bold red]Finalization error:[/bold red] {exc}")
        raise typer.Exit(1) from None


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
