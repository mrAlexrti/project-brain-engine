from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(
    name="brain",
    help="Question-driven context engine for AI-assisted software development.",
    no_args_is_help=True,
)

console = Console()


@app.command()
def version() -> None:
    """Show the installed Project Brain Engine version."""
    console.print("[bold cyan]Project Brain Engine[/bold cyan] 0.1.0")


@app.command()
def context(
    task: Annotated[
        str,
        typer.Argument(help="Task that must be understood before implementation."),
    ],
) -> None:
    """Analyze a task and identify required project questions."""
    console.print("[bold]Task:[/bold]", task)
    console.print()
    console.print("[yellow]Context analysis is not implemented yet.[/yellow]")


if __name__ == "__main__":
    app()
