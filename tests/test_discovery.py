import hashlib
from pathlib import Path
import re
import subprocess

from fastapi.testclient import TestClient
from typer.testing import CliRunner
import yaml

from brain_engine.application import create_app
from brain_engine.cli import app
from brain_engine.discovery import DiscoveryService, ScanLimits
from brain_engine.initialization import InitializationRequest, initialize_brain
from brain_engine.validation import validate_path


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        encoding="utf-8",
    ).stdout.strip()


def repository(tmp_path: Path, files: dict[str, str], name: str = "repository") -> Path:
    root = tmp_path / name
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")
    return root


def post(client: TestClient, path: str, data: dict[str, str] | None = None):
    client.get("/")
    return client.post(
        path, data={**(data or {}), "csrf_token": client.cookies["brain_csrf"]},
        headers={"Origin": "http://testserver"},
    )


def test_python_scan_is_deterministic_linked_and_immutable(tmp_path: Path) -> None:
    root = repository(tmp_path, {
        "README.md": "# Café API\n\nServes Unicode-aware catalog information locally.\n",
        "pyproject.toml": (
            "[project]\nname='cafe-api'\nversion='1'\n"
            "dependencies=['fastapi>=1', 'pytest>=8']\n"
            "[project.scripts]\ncafe='café.main:run'\n"
        ),
        "café/main.py": "def run():\n    return 'привіт'\n",
        "tests/test_main.py": "def test_ok(): assert True\n",
    })
    service = DiscoveryService(tmp_path / "data")
    first = service.scan(root)
    second = service.scan(root)
    assert first["findings"] == second["findings"]
    assert first["metadata"]["repository_sha"] == git(root, "rev-parse", "HEAD")
    assert [first["metadata"]["revision"], second["metadata"]["revision"]] == [1, 2]
    assert "Café API" in Path(first["report_path"]).read_text(encoding="utf-8")
    evidence_ids = {item["evidence_id"] for item in first["evidence"]}
    assert all(set(item["evidence_refs"]) <= evidence_ids for item in first["findings"])
    assert all(item["status"] == "proposed" for item in first["proposals"])
    revision = Path(first["report_path"]).parent
    for name, expected in first["metadata"]["artifact_sha256"].items():
        assert hashlib.sha256((revision / name).read_bytes()).hexdigest() == expected


def test_node_commands_lockfile_and_fake_environment_values_are_safe(tmp_path: Path) -> None:
    fake_secret = "never-store-this-fake-secret-value"
    root = repository(tmp_path, {
        "README.md": "# Web App\n\nA browser application for reviewing work.\n",
        "package.json": (
            '{"name":"web-app","scripts":{"test":"vitest","build":"vite build"},'
            '"dependencies":{"react":"1"},"devDependencies":{"vitest":"1"}}'
        ),
        "package-lock.json": "{}\n",
        ".env.example": f"API_TOKEN={fake_secret}\nEMPTY=\nPUBLIC_URL=https://invalid.example\n",
        "index.js": "console.log('safe')\n",
    })
    report = DiscoveryService(tmp_path / "data").scan(root)
    serialized = yaml.safe_dump(report, allow_unicode=True)
    assert fake_secret not in serialized
    env = next(item for item in report["findings"] if item["kind"] == "environment_variables")
    assert env["normalized_value"] == ["API_TOKEN", "EMPTY", "PUBLIC_URL"]
    assert any(item["normalized_value"] == "npm" for item in report["findings"])
    assert {"React", "Vitest"} <= {
        item["normalized_value"] for item in report["findings"] if item["kind"] == "framework"
    }


def test_mixed_project_is_uncertain_and_documentation_conflict_is_explicit(tmp_path: Path) -> None:
    mixed = repository(tmp_path, {
        "README.md": "# Mixed\n\nA mixed implementation without one declared primary language.\n",
        "pyproject.toml": "[project]\nname='mixed'\nversion='1'\n",
        "package.json": '{"name":"mixed"}',
    }, "mixed")
    mixed_report = DiscoveryService(tmp_path / "mixed-data").scan(mixed)
    assert any(item["question_id"] == "question-discovery-primary-language" for item in mixed_report["questions"])
    assert not any(item["kind"] == "language" for item in mixed_report["conflicts"])

    conflict = repository(tmp_path, {
        "README.md": "# Different Name\n\nThis Python service processes local records.\n",
        "package.json": '{"name":"node-service"}',
    }, "conflict")
    conflict_report = DiscoveryService(tmp_path / "conflict-data").scan(conflict)
    kinds = {item["kind"] for item in conflict_report["conflicts"]}
    assert {"project_name", "language"} <= kinds
    assert all(item["review_status"] == "unresolved" for item in conflict_report["conflicts"])
    service = DiscoveryService(tmp_path / "conflict-data")
    revision = conflict_report["metadata"]["revision"]
    question = conflict_report["questions"][0]
    service.answer_question(
        conflict_report["metadata"]["project_id"], revision,
        question["question_id"], "I do not know",
    )
    conflict_item = conflict_report["conflicts"][0]
    service.review_conflict(
        conflict_report["metadata"]["project_id"], revision,
        conflict_item["conflict_id"], "uncertain",
    )
    reviewed = service.load(conflict_report["metadata"]["project_id"], revision)
    assert next(item for item in reviewed["questions"] if item["question_id"] == question["question_id"])["answer"] == "I do not know"
    assert next(item for item in reviewed["conflicts"] if item["conflict_id"] == conflict_item["conflict_id"])["review_status"] == "uncertain"


def test_stale_limits_exclusions_and_symlinks(tmp_path: Path) -> None:
    root = repository(tmp_path, {
        "README.md": "# Limits\n\nA bounded scanner fixture project.\n",
        "large.txt": "x" * 300,
        "node_modules/tracked.js": "generated",
        "deep/a/b/c/d/file.py": "ignored = True",
    })
    link = root / "linked-readme"
    try:
        link.symlink_to(root / "README.md")
        git(root, "add", "linked-readme")
        git(root, "commit", "-m", "symlink")
    except OSError:
        link = None
    service = DiscoveryService(tmp_path / "data", limits=ScanLimits(
        max_files=10, max_depth=3, max_file_bytes=128, max_excerpt_bytes=40,
        max_total_bytes=256,
    ))
    report = service.scan(root)
    reasons = {(item["path"], item["reason"]) for item in report["skipped_or_partial"]}
    assert ("node_modules", "excluded area") in reasons
    if link is not None:
        assert ("linked-readme", "symbolic link or non-file") in reasons
    (root / "changed.txt").write_text("next", encoding="utf-8")
    git(root, "add", "changed.txt")
    git(root, "commit", "-m", "new head")
    assert service.load(report["metadata"]["project_id"], 1)["stale"] is True


def test_review_actions_create_only_proposed_items_and_do_not_overwrite(tmp_path: Path) -> None:
    root = repository(tmp_path, {
        "README.md": "# Review Demo\n\nA directly documented review workflow demonstration.\n",
        "pyproject.toml": "[project]\nname='review-demo'\nversion='1'\n",
    })
    service = DiscoveryService(tmp_path / "data")
    report = service.scan(root)
    revision = report["metadata"]["revision"]
    accepted, rejected, uncertain = report["proposals"][:3]
    service.review(report["metadata"]["project_id"], revision, accepted["proposal_id"], "accept", content="Owner-edited content")
    service.review(report["metadata"]["project_id"], revision, rejected["proposal_id"], "reject")
    service.review(report["metadata"]["project_id"], revision, uncertain["proposal_id"], "uncertain")
    brain = tmp_path / "managed" / ".brain"
    initialize_brain(InitializationRequest(brain, "Managed", "Purpose", "Python", "en"))
    created = service.create_reviewed_items(
        report["metadata"]["project_id"], revision, brain, confirmed=True,
    )
    assert len(created) == 1
    item = next(item for item in validate_path(brain).items if item.metadata.get("origin") == "discovery")
    assert item.status == "proposed"
    assert "Owner-edited content" in item.content


def test_application_analysis_csrf_review_and_cli_scan(tmp_path: Path) -> None:
    root = repository(tmp_path, {
        "README.md": "# Browser Demo\n\nA local browser discovery demonstration.\n",
        "pyproject.toml": "[project]\nname='browser-demo'\nversion='1'\n",
    })
    data = tmp_path / "app-data"
    client = TestClient(create_app(data))
    connected = post(client, "/projects/connect", {"path": str(root)})
    project_id = re.search(r"/projects/([0-9a-f]+)/analyze", connected.text).group(1)
    page = client.get(f"/projects/{project_id}/analyze")
    assert "Private, bounded, local inspection" in page.text
    token = client.cookies["brain_csrf"]
    assert client.post(
        f"/projects/{project_id}/analyze", data={"csrf_token": token},
        headers={"Origin": "http://evil.invalid"},
    ).status_code == 403
    analyzed = post(client, f"/projects/{project_id}/analyze")
    assert "Evidence details" in analyzed.text
    assert "never automatically approved" not in analyzed.text
    assert "does not approve Project Brain knowledge" in analyzed.text

    result = CliRunner().invoke(app, ["scan", str(root), "--data-dir", str(tmp_path / "cli-data")])
    assert result.exit_code == 0
    assert all(label in result.stdout for label in (
        "Project ID:", "Repository SHA:", "Revision:", "Counts:", "Report:",
    ))
