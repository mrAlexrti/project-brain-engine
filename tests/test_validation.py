from pathlib import Path

import pytest
from typer.testing import CliRunner

from brain_engine.cli import app
from brain_engine.validation import validate_path

START = "<!-- brain:item:start -->"
END = "<!-- brain:item:end -->"


def item(metadata: str = "id: valid.item\ntype: knowledge\nrevision: 1\nstatus: approved", content: str = "Content.\n") -> str:
    return f"{START}\n```yaml\n{metadata}\n```\n\n{content}{END}\n"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def codes(path: Path) -> list[str]:
    return [issue.code for issue in validate_path(path).issues]


def test_valid_item_and_source_locations(tmp_path: Path) -> None:
    path = write(tmp_path / "brain.md", item())
    result = validate_path(path)
    assert result.success
    assert len(result.items) == 1
    parsed = result.items[0]
    assert (parsed.id, parsed.type, parsed.revision, parsed.status) == ("valid.item", "knowledge", 1, "approved")
    assert (parsed.start_line, parsed.metadata_line, parsed.end_line) == (1, 2, 10)


def test_multiple_items_and_markdown_extraction(tmp_path: Path) -> None:
    text = item(content="# Heading\n\nA **rich** paragraph.\n") + item(
        "id: second\ntype: decision\nrevision: 2\nstatus: proposed"
    )
    result = validate_path(write(tmp_path / "brain.md", text))
    assert [parsed.id for parsed in result.items] == ["valid.item", "second"]
    assert result.items[0].content == "# Heading\n\nA **rich** paragraph.\n"


def test_unknown_metadata_is_preserved(tmp_path: Path) -> None:
    result = validate_path(write(tmp_path / "brain.md", item(content="", metadata="id: valid\ntype: knowledge\nrevision: 1\nstatus: approved\nextension:\n  enabled: true")))
    assert result.success
    assert result.items[0].metadata["extension"] == {"enabled": True}


def test_recursive_scan_and_deterministic_order(tmp_path: Path) -> None:
    write(tmp_path / "z.md", item("id: z\ntype: knowledge\nrevision: 1\nstatus: approved"))
    write(tmp_path / "nested" / "a.md", item("id: a\ntype: knowledge\nrevision: 1\nstatus: approved"))
    write(tmp_path / "ignored.txt", item())
    result = validate_path(tmp_path)
    assert [path.relative_to(tmp_path).as_posix() for path in result.files_scanned] == ["nested/a.md", "z.md"]
    assert [parsed.id for parsed in result.items] == ["a", "z"]


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ("type: knowledge\nrevision: 1\nstatus: approved", "BRAIN101"),
        ("id: Bad ID\ntype: knowledge\nrevision: 1\nstatus: approved", "BRAIN102"),
        ("id: valid\ntype: other\nrevision: 1\nstatus: approved", "BRAIN103"),
        ("id: valid\ntype: knowledge\nrevision: 1\nstatus: other", "BRAIN105"),
        ("id: valid\ntype: knowledge\nrevision: 0\nstatus: approved", "BRAIN104"),
        ("id: valid\ntype: knowledge\nrevision: -1\nstatus: approved", "BRAIN104"),
        ("id: valid\ntype: knowledge\nrevision: true\nstatus: approved", "BRAIN104"),
        ("id: valid\ntype: knowledge\nrevision: 1\nstatus: approved\nclassification: opinion", "BRAIN106"),
        ("id: valid\ntype: knowledge\nrevision: 1\nstatus: approved\nseverity: urgent", "BRAIN107"),
        ("id: valid\ntype: knowledge\nrevision: 1\nstatus: approved\nsources: source.py", "BRAIN108"),
        ("id: valid\ntype: knowledge\nrevision: 1\nstatus: approved\ntags: [ok, 3]", "BRAIN108"),
    ],
)
def test_metadata_validation(tmp_path: Path, metadata: str, expected: str) -> None:
    assert expected in codes(write(tmp_path / "brain.md", item(metadata)))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (f"{START}\n```yaml\nid: [broken\n```\n{END}\n", "BRAIN005"),
        (f"{START}\n```yaml\n- one\n- two\n```\n{END}\n", "BRAIN006"),
        (f"{START}\nNo metadata.\n{END}\n", "BRAIN004"),
        (f"{START}\n```yaml\nid: valid\n{END}\n", "BRAIN007"),
        (f"{START}\n```yaml\nid: one\ntype: knowledge\nrevision: 1\nstatus: approved\n```\n{START}\n{END}\n{END}\n", "BRAIN002"),
        (f"{END}\n", "BRAIN001"),
        (f"{START}\n```yaml\nid: valid\n", "BRAIN003"),
    ],
)
def test_parser_errors(tmp_path: Path, text: str, expected: str) -> None:
    assert expected in codes(write(tmp_path / "brain.md", text))


def test_duplicate_id_in_one_file(tmp_path: Path) -> None:
    assert "BRAIN109" in codes(write(tmp_path / "brain.md", item() + item()))


def test_duplicate_id_across_files(tmp_path: Path) -> None:
    write(tmp_path / "a.md", item())
    write(tmp_path / "b.md", item())
    assert "BRAIN109" in codes(tmp_path)


def test_cli_valid_invalid_and_missing_paths(tmp_path: Path) -> None:
    runner = CliRunner()
    valid = write(tmp_path / "valid.md", item())
    invalid = write(tmp_path / "invalid.md", item("id: Invalid\ntype: knowledge\nrevision: 1\nstatus: approved"))
    valid_result = runner.invoke(app, ["validate", str(valid)])
    invalid_result = runner.invoke(app, ["validate", str(invalid)])
    missing_result = runner.invoke(app, ["validate", str(tmp_path / "missing")])
    assert valid_result.exit_code == 0
    assert "Brain Items found" in valid_result.stdout
    assert invalid_result.exit_code == 1
    assert "BRAIN102" in invalid_result.stdout
    assert missing_result.exit_code == 2
    assert "Operational error" in missing_result.stdout
    assert missing_result.exception is not None


def test_cli_empty_directory_succeeds(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 0
    assert "Validation summary" in result.stdout


@pytest.mark.parametrize(
    "fence",
    ["```markdown", "~~~text"],
)
def test_markers_inside_code_examples_are_ignored(tmp_path: Path, fence: str) -> None:
    closing_fence = fence[0] * 3
    example = f"{fence}\n{START}\nnot metadata\n{END}\n{closing_fence}\n"
    result = validate_path(write(tmp_path / "example.md", example))
    assert result.success
    assert result.items == []


def test_real_item_after_ignored_example_is_parsed(tmp_path: Path) -> None:
    example = f"````markdown\n{START}\n```yaml\nid: example\n```\n{END}\n````\n"
    result = validate_path(write(tmp_path / "example.md", example + item()))
    assert result.success
    assert [parsed.id for parsed in result.items] == ["valid.item"]
    assert result.items[0].start_line == 8


def test_markers_in_item_content_fence_do_not_affect_item(tmp_path: Path) -> None:
    content = f"Before.\n\n~~~markdown\n{START}\n{END}\n~~~\n\nAfter.\n"
    result = validate_path(write(tmp_path / "content.md", item(content=content)))
    assert result.success
    assert len(result.items) == 1
    assert result.items[0].content == content
    assert result.items[0].end_line == 17


def test_cli_validates_documentation_tree() -> None:
    docs = Path(__file__).parents[1] / "docs"
    result = CliRunner().invoke(app, ["validate", str(docs)])
    assert result.exit_code == 0, result.stdout
    assert "0" in result.stdout
