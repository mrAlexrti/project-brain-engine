import os
from pathlib import Path
import subprocess
import sys
import zipfile


def test_installed_wheel_contains_and_serves_templates_and_static_assets(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(wheel_dir), "."],
        check=True, capture_output=True, text=True,
    )
    wheel = next(wheel_dir.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    assert "brain_engine/application/templates/base.html" in names
    assert "brain_engine/application/templates/projects/onboarding.html" in names
    assert "brain_engine/application/static/app.css" in names
    target = tmp_path / "installed"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheel)],
        check=True, capture_output=True, text=True,
    )
    script = (
        "import sys;sys.path.insert(0, r'" + str(target) + "');"
        "from pathlib import Path;"
        "from fastapi.testclient import TestClient;"
        "from brain_engine.application import create_app;"
        "c=TestClient(create_app(Path(r'" + str(tmp_path / "data") + "')));"
        "assert c.get('/').status_code == 200;assert c.get('/static/app.css').status_code == 200"
    )
    environment = {**os.environ, "PYTHONPATH": ""}
    subprocess.run([sys.executable, "-c", script], cwd=tmp_path, env=environment, check=True)
