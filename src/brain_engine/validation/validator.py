"""Metadata and file-set validation for Brain Items."""

import re
from pathlib import Path

from brain_engine.domain import BrainItem, ValidationIssue, ValidationResult
from brain_engine.parser import parse_markdown_file

REQUIRED_FIELDS = ("id", "type", "revision", "status")
ALLOWED_TYPES = frozenset({"knowledge", "question", "contract", "decision", "playbook", "verification"})
ALLOWED_STATUSES = frozenset({"proposed", "approved", "deprecated"})
ALLOWED_CLASSIFICATIONS = frozenset({"fact", "assumption", "risk", "recommendation"})
ALLOWED_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
LIST_FIELDS = ("sources", "tags", "relations")
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


class ValidationOperationalError(Exception):
    """An expected failure while locating or reading validation input."""


def _error(item: BrainItem, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(code, message, "error", item.source_path, item.metadata_line)


def _validate_item(item: BrainItem) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in REQUIRED_FIELDS:
        if field not in item.metadata:
            issues.append(_error(item, "BRAIN101", f"Missing required field: {field}."))
    if "id" in item.metadata and (not isinstance(item.id, str) or not item.id or ID_PATTERN.fullmatch(item.id) is None):
        issues.append(_error(item, "BRAIN102", "ID must match ^[a-z0-9]+(?:[._-][a-z0-9]+)*$."))
    if "type" in item.metadata and (
        not isinstance(item.type, str) or item.type not in ALLOWED_TYPES
    ):
        issues.append(_error(item, "BRAIN103", f"Invalid Brain Item type: {item.type!r}."))
    if "revision" in item.metadata and (isinstance(item.revision, bool) or not isinstance(item.revision, int) or item.revision <= 0):
        issues.append(_error(item, "BRAIN104", "Revision must be a positive integer."))
    if "status" in item.metadata and (
        not isinstance(item.status, str) or item.status not in ALLOWED_STATUSES
    ):
        issues.append(_error(item, "BRAIN105", f"Invalid status: {item.status!r}."))
    classification = item.metadata.get("classification")
    if "classification" in item.metadata and (
        not isinstance(classification, str) or classification not in ALLOWED_CLASSIFICATIONS
    ):
        issues.append(_error(item, "BRAIN106", f"Invalid classification: {classification!r}."))
    severity = item.metadata.get("severity")
    if "severity" in item.metadata and (
        not isinstance(severity, str) or severity not in ALLOWED_SEVERITIES
    ):
        issues.append(_error(item, "BRAIN107", f"Invalid severity: {severity!r}."))
    for field in LIST_FIELDS:
        value = item.metadata.get(field)
        if field in item.metadata and (not isinstance(value, list) or any(not isinstance(entry, str) for entry in value)):
            issues.append(_error(item, "BRAIN108", f"{field} must be a list of strings."))
    return issues


def _input_files(path: Path) -> list[Path]:
    if not path.exists():
        raise ValidationOperationalError(f"Path does not exist: {path}")
    if path.is_file():
        if path.suffix.lower() != ".md":
            raise ValidationOperationalError(f"Path is not a Markdown file: {path}")
        return [path]
    if not path.is_dir():
        raise ValidationOperationalError(f"Path is neither a file nor directory: {path}")
    try:
        return sorted((candidate for candidate in path.rglob("*.md") if candidate.is_file()), key=lambda p: p.as_posix())
    except OSError as exc:
        raise ValidationOperationalError(f"Cannot scan path {path}: {exc}") from exc


def validate_path(path: Path) -> ValidationResult:
    """Parse and validate a Markdown file or recursive directory tree."""
    files = _input_files(path)
    result = ValidationResult(files_scanned=files)
    for file_path in files:
        try:
            items, issues = parse_markdown_file(file_path)
        except (OSError, UnicodeError) as exc:
            raise ValidationOperationalError(f"Cannot read {file_path}: {exc}") from exc
        result.items.extend(items)
        result.issues.extend(issues)
        for item in items:
            result.issues.extend(_validate_item(item))
    first_by_id: dict[str, BrainItem] = {}
    for item in result.items:
        if not isinstance(item.id, str) or ID_PATTERN.fullmatch(item.id) is None:
            continue
        if item.id in first_by_id:
            first = first_by_id[item.id]
            result.issues.append(_error(item, "BRAIN109", f"Duplicate ID {item.id!r}; first defined at {first.source_path}:{first.metadata_line}."))
        else:
            first_by_id[item.id] = item
    return result
