from pathlib import Path

from typer.testing import CliRunner

from brain_engine.cli import app
from brain_engine.initialization import BrainExistsError, InitializationRequest, initialize_brain
from brain_engine.validation import validate_path


def test_initialize_proposed_valid_utf8_brain(tmp_path: Path) -> None:
    result = initialize_brain(InitializationRequest(tmp_path, "Проєкт Дія", "Зберігає точний текст", "Python", "uk"))
    validation = validate_path(result.brain_path)
    assert validation.success
    assert validation.items
    assert {item.status for item in validation.items} == {"proposed"}
    for path in result.created_files:
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert "Зберігає точний текст" in (result.brain_path / "PROJECT_INTAKE.md").read_text(encoding="utf-8")


def test_initialize_refuses_nonempty_brain(tmp_path: Path) -> None:
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "user.md").write_text("owned", encoding="utf-8")
    try:
        initialize_brain(InitializationRequest(tmp_path, "Name", "Purpose", "Python"))
    except BrainExistsError:
        pass
    else:
        raise AssertionError("Expected overwrite refusal")
    assert (brain / "user.md").read_text(encoding="utf-8") == "owned"


def test_noninteractive_cli_is_deterministic(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["init", "--path", str(tmp_path), "--non-interactive", "--project-name", "Demo", "--project-purpose", "Purpose", "--primary-technology", "Python", "--language", "en"])
    assert result.exit_code == 0, result.stdout
    assert "No project knowledge was automatically approved" in result.stdout
