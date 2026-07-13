"""Shared initialization service for the CLI and local application."""

from pathlib import Path

from brain_engine.initialization.models import InitializationRequest, InitializationResult
from brain_engine.initialization.templates import item_markdown
from brain_engine.persistence import atomic_write_text
from brain_engine.validation import validate_path


class BrainExistsError(ValueError):
    pass


def _slug(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "project"


def initialize_brain(request: InitializationRequest) -> InitializationResult:
    root = request.path.resolve()
    brain = root if root.name == ".brain" else root / ".brain"
    if brain.exists() and any(brain.iterdir()):
        raise BrainExistsError(f"Refusing to overwrite non-empty Brain directory: {brain}")
    brain.mkdir(parents=True, exist_ok=True)
    directories = ("knowledge", "decisions", "contracts", "questions", "playbooks", "verification")
    for directory in directories:
        (brain / "items" / directory).mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    readme = brain / "README.md"
    atomic_write_text(readme, "# Project Brain\n\nOwner-reviewed project knowledge. New Items start as `proposed`.\n")
    created.append(readme)
    intake = brain / "PROJECT_INTAKE.md"
    atomic_write_text(
        intake,
        f"# Project Intake\n\n- Name: {request.project_name}\n- Language: {request.language}\n"
        f"- Primary technology: {request.primary_technology}\n\n{request.project_purpose}\n",
    )
    created.append(intake)
    items = (
        ("knowledge/project-name.md", {"id": f"project.{_slug(request.project_name)}.name", "type": "knowledge", "classification": "fact", "title": "Project name", "sources": [".brain/PROJECT_INTAKE.md"]}, request.project_name),
        ("knowledge/project-purpose.md", {"id": "project.purpose", "type": "knowledge", "classification": "fact", "title": "Project purpose", "sources": [".brain/PROJECT_INTAKE.md"]}, request.project_purpose),
        ("knowledge/primary-technology.md", {"id": "project.primary-technology", "type": "knowledge", "classification": "fact", "title": "Primary technology", "keywords": [_slug(request.primary_technology)], "sources": [".brain/PROJECT_INTAKE.md"]}, request.primary_technology),
    )
    for relative, metadata, content in items:
        target = brain / "items" / relative
        atomic_write_text(target, item_markdown(metadata, content))
        created.append(target)
    result = validate_path(brain)
    if not result.success:
        raise RuntimeError("Generated Brain failed validation.")
    return InitializationResult(brain, tuple(created), len(result.items), result.error_count)
