"""Core domain objects for parsed Brain Items and validation results."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class BrainItem:
    """A Brain Item parsed from its canonical Markdown representation."""

    id: object
    type: object
    revision: object
    status: object
    metadata: dict[str, Any]
    content: str
    source_path: Path
    start_line: int
    end_line: int
    metadata_line: int


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A stable, user-facing parsing or metadata validation issue."""

    code: str
    message: str
    severity: str
    path: Path
    line: int


@dataclass(slots=True)
class ValidationResult:
    """The complete result of validating one file or directory."""

    items: list[BrainItem] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    files_scanned: list[Path] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(issue.severity == "error" for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)

    @property
    def success(self) -> bool:
        return self.error_count == 0
