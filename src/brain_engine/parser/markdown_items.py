"""Deterministic parser for Brain Items embedded in Markdown."""

from pathlib import Path
from typing import Any

import yaml

from brain_engine.domain import BrainItem, ValidationIssue

START_MARKER = "<!-- brain:item:start -->"
END_MARKER = "<!-- brain:item:end -->"
YAML_FENCE = "```yaml"
FENCE_END = "```"


def _issue(code: str, message: str, path: Path, line: int) -> ValidationIssue:
    return ValidationIssue(code, message, "error", path, line)


def _fence_run(line: str) -> tuple[str, int, str] | None:
    """Return the fence character, run length, and remaining text when fenced."""
    stripped = line.lstrip()
    if not stripped or stripped[0] not in ("`", "~"):
        return None
    character = stripped[0]
    length = len(stripped) - len(stripped.lstrip(character))
    if length < 3:
        return None
    return character, length, stripped[length:]


def _update_fence(
    line: str, active_fence: tuple[str, int] | None
) -> tuple[str, int] | None:
    """Update Markdown fence state for one line."""
    fence = _fence_run(line)
    if fence is None:
        return active_fence
    character, length, remainder = fence
    if active_fence is None:
        return character, length
    opening_character, opening_length = active_fence
    if character == opening_character and length >= opening_length and not remainder.strip():
        return None
    return active_fence


def _parse_block(
    lines: list[str], path: Path, start_index: int, end_index: int
) -> tuple[BrainItem | None, list[ValidationIssue]]:
    first = start_index + 1
    while first < end_index and not lines[first].strip():
        first += 1
    if first >= end_index or lines[first].strip() != YAML_FENCE:
        line = first + 1 if first < end_index else start_index + 1
        return None, [
            _issue(
                "BRAIN004",
                "The first non-empty Item content must be a ```yaml metadata block.",
                path,
                line,
            )
        ]
    fence_end = first + 1
    while fence_end < end_index and lines[fence_end].strip() != FENCE_END:
        fence_end += 1
    if fence_end >= end_index:
        return None, [_issue("BRAIN007", "YAML metadata fence is not terminated.", path, first + 1)]
    yaml_text = "".join(lines[first + 1 : fence_end])
    try:
        loaded = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        problem_line = first + 2
        if getattr(exc, "problem_mark", None) is not None:
            problem_line += exc.problem_mark.line
        return None, [_issue("BRAIN005", "Malformed YAML metadata.", path, problem_line)]
    if not isinstance(loaded, dict):
        return None, [_issue("BRAIN006", "YAML metadata root must be a mapping.", path, first + 1)]
    metadata: dict[str, Any] = loaded
    content_lines = lines[fence_end + 1 : end_index]
    if content_lines and not content_lines[0].strip():
        content_lines = content_lines[1:]
    content = "".join(content_lines)
    return BrainItem(
        id=metadata.get("id"), type=metadata.get("type"), revision=metadata.get("revision"),
        status=metadata.get("status"), metadata=metadata, content=content, source_path=path,
        start_line=start_index + 1, end_line=end_index + 1, metadata_line=first + 1,
    ), []


def parse_markdown_file(path: Path) -> tuple[list[BrainItem], list[ValidationIssue]]:
    """Parse all canonical Brain Items in a UTF-8 Markdown file."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    items: list[BrainItem] = []
    issues: list[ValidationIssue] = []
    open_index: int | None = None
    active_fence: tuple[str, int] | None = None
    awaiting_metadata = False
    in_metadata_fence = False
    for index, line in enumerate(lines):
        token = line.strip()
        if in_metadata_fence:
            if token == FENCE_END:
                in_metadata_fence = False
                continue
            if token not in (START_MARKER, END_MARKER):
                continue
        elif awaiting_metadata:
            if not token:
                continue
            awaiting_metadata = False
            if token == YAML_FENCE:
                in_metadata_fence = True
                continue

        previous_fence = active_fence
        active_fence = _update_fence(line, active_fence)
        if previous_fence is not None or active_fence is not None:
            continue
        if token == START_MARKER:
            if open_index is not None:
                issues.append(_issue("BRAIN002", "Nested opening marker.", path, index + 1))
            else:
                open_index = index
                awaiting_metadata = True
        elif token == END_MARKER:
            if open_index is None:
                issues.append(
                    _issue(
                        "BRAIN001",
                        "Closing marker without an opening marker.",
                        path,
                        index + 1,
                    )
                )
            else:
                item, block_issues = _parse_block(lines, path, open_index, index)
                if item is not None:
                    items.append(item)
                issues.extend(block_issues)
                open_index = None
                awaiting_metadata = False
                in_metadata_fence = False
    if open_index is not None:
        issues.append(_issue("BRAIN003", "Brain Item is not closed.", path, open_index + 1))
    return items, issues
