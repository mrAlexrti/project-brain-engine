from pathlib import Path
import hashlib
import re
import subprocess
from datetime import datetime

from fastapi.testclient import TestClient
import yaml

from brain_engine.application import create_app
from brain_engine.application.launcher import is_loopback, select_port
from brain_engine.experiment import ExperimentService


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def post(client: TestClient, path: str, data: dict[str, str] | None = None):
    client.get("/")
    values = {**(data or {}), "csrf_token": client.cookies["brain_csrf"]}
    return client.post(path, data=values, headers={"Origin": "http://testserver"})


def test_home_assets_connect_and_safe_errors(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.email", "test@example.invalid")
    git(repository, "config", "user.name", "Test")
    (repository / "pyproject.toml").write_text("[project]\nname='demo'\nversion='1'\n", encoding="utf-8")
    git(repository, "add", "pyproject.toml")
    git(repository, "commit", "-m", "baseline")
    client = TestClient(create_app(tmp_path / "data"))
    assert client.get("/").status_code == 200
    assert "All data remains local" in client.get("/").text
    assert client.get("/static/app.css").status_code == 200
    connected = post(client, "/projects/connect", {"path": str(repository)})
    assert connected.status_code == 200
    assert "Candidate — requires owner confirmation" in connected.text
    invalid = post(client, "/projects/connect", {"path": str(tmp_path / "missing")})
    assert invalid.status_code == 400
    assert "Traceback" not in invalid.text


def test_local_binding_helpers() -> None:
    assert is_loopback("127.0.0.1")
    assert not is_loopback("0.0.0.0")
    assert select_port("127.0.0.1", 0) >= 1


def test_get_routes_do_not_expose_private_mapping(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    for path in ("/", "/projects/connect", "/create-experiment"):
        response = client.get(path)
        assert "treatment-map" not in response.text
    assert client.get("/experiments/..%2Fprivate").status_code == 404


def test_state_changes_require_strict_origin_and_csrf(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "data"))
    client.get("/projects/connect")
    token = client.cookies["brain_csrf"]
    assert client.post("/projects/connect", data={"path": "x", "csrf_token": token}).status_code == 403
    assert client.post(
        "/projects/connect", data={"path": "x", "csrf_token": "wrong"},
        headers={"Origin": "http://testserver"},
    ).status_code == 403
    assert client.post(
        "/projects/connect", data={"path": "x", "csrf_token": token},
        headers={"Origin": "http://evil.invalid"},
    ).status_code == 403


def test_complete_application_first_onboarding(tmp_path: Path, monkeypatch) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init")
    git(repository, "config", "user.email", "test@example.invalid")
    git(repository, "config", "user.name", "Test")
    (repository / "README.md").write_text("demo\n", encoding="utf-8")
    git(repository, "add", "README.md")
    git(repository, "commit", "-m", "baseline")
    client = TestClient(create_app(tmp_path / "data"))
    connected = post(client, "/projects/connect", {"path": str(repository)})
    project_id = re.search(r"/projects/([0-9a-f]+)/onboarding", connected.text).group(1)
    page = client.get(f"/projects/{project_id}/onboarding")
    assert all(label in page.text for label in ("Project intake", "Brain initialization", "Preflight"))
    initialized = post(client, f"/projects/{project_id}/brain/init", {
        "project_name": "Demo", "project_purpose": "Test application onboarding",
        "primary_technology": "Python", "language": "en",
    })
    assert initialized.status_code == 200
    created = post(client, f"/projects/{project_id}/items/new", {
        "item_id": "question.owner", "item_type": "question", "title": "Owner",
        "content": "Who owns this?",
    })
    assert created.status_code == 200
    assert (tmp_path / "data/brains" / project_id / ".brain/items/questions/question.owner.md").is_file()
    edited = post(client, f"/projects/{project_id}/items/question.owner/edit", {
        "item_id": "question.owner", "item_type": "question", "title": "Responsible owner",
        "content": "Who is the responsible owner?",
    })
    assert edited.status_code == 200
    approved = post(client, f"/projects/{project_id}/items/question.owner/approve", {"confirmed": "yes"})
    assert approved.status_code == 200
    preview = post(client, f"/projects/{project_id}/context/preview", {
        "task": "Review the demo", "answers": "question.owner=Project owner",
    })
    assert "question.owner" in preview.text
    frozen = post(client, f"/projects/{project_id}/context/freeze", {
        "task": "Review the demo", "answers": "question.owner=Project owner",
    })
    assert frozen.status_code == 200
    restored = client.get(f"/projects/{project_id}/onboarding")
    assert "Review the demo" in restored.text
    assert "question.owner=Project owner" in restored.text
    index_path = tmp_path / "data/context-packages" / project_id / "index.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    snapshot = index["revisions"][0]
    snapshot_root = index_path.parent
    assert snapshot["revision"] == 1
    assert datetime.fromisoformat(snapshot["frozen_at"]).utcoffset() is not None
    assert snapshot["task_sha256"] == hashlib.sha256(
        (snapshot_root / snapshot["task_path"]).read_bytes()
    ).hexdigest()
    assert snapshot["context_sha256"] == hashlib.sha256(
        (snapshot_root / snapshot["context_path"]).read_bytes()
    ).hexdigest()
    refused = post(client, f"/projects/{project_id}/context/freeze", {
        "task": "Review the demo", "answers": "question.owner=Project owner",
    })
    assert refused.status_code == 400
    assert "explicit new revision" in refused.text
    revised = post(client, f"/projects/{project_id}/context/freeze", {
        "task": "Review the revised demo", "answers": "question.owner=Project owner",
        "new_revision": "yes",
    })
    assert revised.status_code == 200
    revisions = yaml.safe_load(index_path.read_text(encoding="utf-8"))["revisions"]
    assert [item["revision"] for item in revisions] == [1, 2]
    assert revisions[0] == snapshot
    assert (snapshot_root / snapshot["context_path"]).is_file()
    preflight = post(client, f"/projects/{project_id}/preflight")
    assert "Context Frozen" in preflight.text
    assert f"/create-experiment?project_id={project_id}" in preflight.text
    creation = client.get(f"/create-experiment?project_id={project_id}")
    assert str(repository) in creation.text
    assert "Selected frozen inputs" in creation.text
    assert 'name="repository"' not in creation.text
    selected_call = {}

    def initialize(self, repository, output, task, ground_truth, brain_path, **options):
        selected_call.update({
            "repository": repository, "task": task, "brain_path": brain_path,
            "context": options["frozen_context_path"],
            "revision": options["frozen_context_revision"],
        })
        return output

    monkeypatch.setattr(ExperimentService, "initialize", initialize)
    token = client.cookies["brain_csrf"]
    created_experiment = client.post(
        "/create-experiment", data={
            "csrf_token": token, "project_id": project_id, "experiment_id": "selected",
            "ground_truth": "Expected", "privacy": "private",
        }, headers={"Origin": "http://testserver"}, follow_redirects=False,
    )
    assert created_experiment.status_code == 303
    assert selected_call["repository"] == repository
    assert selected_call["brain_path"] == tmp_path / "data/brains" / project_id / ".brain"
    assert selected_call["context"].name == "CONTEXT-r2.yaml"
    assert selected_call["revision"] == 2
    assert selected_call["task"] == "Review the revised demo"
    (repository / "became-dirty.txt").write_text("dirty", encoding="utf-8")
    current_preflight = post(client, f"/projects/{project_id}/preflight")
    assert "Repository Clean</dt><dd>False" in current_preflight.text
