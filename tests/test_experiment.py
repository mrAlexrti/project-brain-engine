import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

from brain_engine.experiment import ExperimentError, ExperimentService
from brain_engine.experiment.evaluation import RUBRIC, lock_evaluation, reveal_treatment
from brain_engine.experiment.storage import load_state
from brain_engine.experiment.evidence import run_verification

from test_context import block, brain


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "source project"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "app.txt").write_text("baseline\n", encoding="utf-8")
    git(root, "add", "app.txt")
    git(root, "commit", "-m", "baseline")
    return root


def approved_brain(tmp_path: Path) -> Path:
    return brain(tmp_path / "knowledge", block("knowledge.test", "knowledge", content="Trusted context."))


def create(tmp_path: Path) -> Path:
    return ExperimentService().initialize(repository(tmp_path), tmp_path / "experiment output", "Исправить bug в Parser42", "Expected behavior", approved_brain(tmp_path))


def test_rejections(tmp_path: Path) -> None:
    source = repository(tmp_path)
    knowledge = approved_brain(tmp_path)
    with pytest.raises(ExperimentError, match="outside"):
        ExperimentService().initialize(source, source / "experiment", "Task", "Truth", knowledge)
    (source / "dirty.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(ExperimentError, match="clean"):
        ExperimentService().initialize(source, tmp_path / "elsewhere", "Task", "Truth", knowledge)


def test_isolation_private_mapping_and_neutral_status(tmp_path: Path) -> None:
    root = create(tmp_path)
    state = load_state(root)
    baseline = state["repository"]["baseline_sha"]
    assert {git(root / name, "rev-parse", "HEAD") for name in ("workspace-1", "workspace-2", "workspace-context")} == {baseline}
    assert not (root / "workspace-1" / ".brain").exists()
    assert not (root / "workspace-2" / ".brain").exists()
    assert (root / "workspace-context" / ".brain").exists()
    mapping = yaml.safe_load((root / "evidence/private/treatment-map.yaml").read_text(encoding="utf-8"))
    assert mapping["context_result"] in {"result-1", "result-2"}
    public, consistent = ExperimentService().status(root)
    assert consistent
    assert public["checks"]["evidence_complete"] is False
    assert "run_order" not in public
    assert "context_result" not in str(public)


def test_status_detects_hash_isolation_and_evaluator_neutrality_failures(tmp_path: Path) -> None:
    root = create(tmp_path)
    task = root / "TASK.md"
    original = task.read_bytes()
    task.write_bytes(original + b"tampered")
    public, consistent = ExperimentService().status(root)
    assert not consistent and public["checks"]["task_hash"] is False
    task.write_bytes(original)
    (root / "workspace-1/.brain").mkdir()
    public, consistent = ExperimentService().status(root)
    assert not consistent and public["checks"]["brain_isolation"] is False
    (root / "workspace-1/.brain").rmdir()
    evaluator = root / "evidence/evaluation/neutral-evaluator-package"
    evaluator.mkdir()
    (evaluator / "unexpected.txt").write_text("not controlled", encoding="utf-8")
    public, consistent = ExperimentService().status(root)
    assert not consistent and public["checks"]["evaluator_package_neutral"] is False


def scores() -> dict[str, dict[str, object]]:
    return {name: {"categories": {category: maximum for category, maximum in RUBRIC.items()}, "evidence": {category: "Observed evidence." for category in RUBRIC}, "unsupported_assumptions": "None", "critical_failure_cap": None} for name in ("result-1", "result-2")}


def test_run_evidence_evaluation_and_finalization(tmp_path: Path) -> None:
    root = create(tmp_path)
    service = ExperimentService()
    for result_name in ("result-1", "result-2"):
        service.start_run(root, result_name)
        workspace = root / ("workspace-1" if result_name == "result-1" else "workspace-2")
        (workspace / f"{result_name}.txt").write_text("change\n", encoding="utf-8")
        service.finish_run(root, result_name, {"final_report": "Done", "permission_prompts": 0, "clarification_questions": 0, "corrective_iterations": 0})
        evidence = service.capture(root, result_name)
        patch = (evidence / "changes.patch").read_text(encoding="utf-8")
        assert (evidence / "patch-sha256.txt").read_text().strip() == hashlib.sha256(patch.encode()).hexdigest()
        assert __import__("datetime").datetime.fromisoformat(
            (evidence / "started-at.txt").read_text().strip()
        ).utcoffset() is not None
        inventory = yaml.safe_load((evidence / "untracked-files.yaml").read_text())
        stored_change = (workspace / f"{result_name}.txt").read_bytes()
        assert inventory["files"][0]["path"] == f"{result_name}.txt"
        assert inventory["files"][0]["sha256"] == hashlib.sha256(stored_change).hexdigest()
        assert (evidence / "untracked-files" / f"{result_name}.txt").read_bytes() == stored_change
    status, _ = service.status(root)
    assert status["checks"]["evidence_complete"] is True
    with pytest.raises(ValueError, match="before"):
        reveal_treatment(root)
    lock_evaluation(root, scores())
    reveal_treatment(root)
    manifest = service.finalize(root)
    assert manifest.exists()
    assert "integrity-manifest-sha256.txt" not in manifest.read_text(encoding="utf-8")
    evaluator_files = [path.name for path in (root / "evidence/evaluation/neutral-evaluator-package").rglob("*")]
    assert "treatment-map.yaml" not in evaluator_files
    final = (root / "evidence/evaluation/final-evaluation.md").read_text(encoding="utf-8")
    assert "Category scores and evidence" in final
    assert "Unsupported assumptions" in final
    assert "Protocol deviations" in final
    assert "Treatment result after reveal" in final
    assert "Comparison classification" in final
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "workspace-1" not in manifest_text
    assert "workspace-context" not in manifest_text


def test_finish_state_persists_across_service_instances_before_capture(tmp_path: Path) -> None:
    root = create(tmp_path)
    ExperimentService().start_run(root, "result-1")
    ExperimentService().finish_run(root, "result-1", {"final_report": "persisted"})
    persisted = load_state(root)["results"]["result-1"]
    assert persisted["state"] == "finished"
    assert persisted["final_report"] == "persisted"
    evidence = ExperimentService().capture(root, "result-1")
    assert (evidence / "agent-final-report.txt").read_text() == "persisted"


@pytest.mark.parametrize("command", [
    ["git", "status"], ["python", "-c", "print('safe looking')"],
    ["python", "-m", "pip", "check"], ["ruff", "server"], ["npm", "run", "deploy"],
    ["ruff", "format", "."], ["ruff", "check", "--fix", "."],
    ["python", "-m", "ruff", "check", "--unsafe-fixes", "."],
])
def test_verification_structured_allowlist_rejects_commands(tmp_path: Path, command: list[str]) -> None:
    with pytest.raises(ValueError, match="allowed|must use|Mutating|only with"):
        run_verification(tmp_path, command, 1)


def test_existing_brain_is_rejected_or_marked_pilot(tmp_path: Path) -> None:
    source = repository(tmp_path)
    (source / ".brain").mkdir()
    (source / ".brain" / "README.md").write_text("baseline brain", encoding="utf-8")
    git(source, "add", ".brain")
    git(source, "commit", "-m", "brain baseline")
    knowledge = approved_brain(tmp_path)
    with pytest.raises(ExperimentError, match="baseline already contains"):
        ExperimentService().initialize(source, tmp_path / "rejected", "Task", "Truth", knowledge)
    root = ExperimentService().initialize(
        source, tmp_path / "pilot", "Task", "Truth", knowledge,
        allow_existing_brain=True,
    )
    assert load_state(root)["comparison"] == {
        "classification": "contaminated-pilot", "reportable_as_clean": False,
    }


def test_task_hash_uses_exact_stored_bytes_and_metadata_is_recorded(tmp_path: Path) -> None:
    root = create(tmp_path)
    state = load_state(root)
    assert (root / "TASK.md").is_file()
    assert state["task"]["sha256"] == hashlib.sha256((root / "TASK.md").read_bytes()).hexdigest()
    assert state["repository"]["head"] == state["repository"]["baseline_sha"]
    assert state["environment"]["python_executable"]


def test_frozen_context_bytes_are_reused_without_regeneration(tmp_path: Path) -> None:
    source = repository(tmp_path)
    knowledge = approved_brain(tmp_path)
    frozen = tmp_path / "frozen-context.yaml"
    content = b"request:\n  task: Task\ncustom: exact-snapshot\n"
    frozen.write_bytes(content)
    root = ExperimentService().initialize(
        source, tmp_path / "frozen experiment", "Task", "Truth", knowledge,
        frozen_context_path=frozen,
    )
    stored = root / "evidence/context-package/context-package.yaml"
    assert stored.read_bytes() == content
    assert load_state(root)["context_package"]["sha256"] == hashlib.sha256(content).hexdigest()
