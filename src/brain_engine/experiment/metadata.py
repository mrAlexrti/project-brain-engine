"""Stable repository metadata detection without source scanning."""

import os
import platform
import sys
from pathlib import Path
from typing import Any

from brain_engine import __version__
from brain_engine.experiment.git import GitService

MARKERS = (
    "pyproject.toml", "requirements.txt", "package.json", "package-lock.json", "pnpm-lock.yaml",
    "yarn.lock", "pom.xml", "build.gradle", "settings.gradle", "Cargo.toml", "go.mod",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Makefile",
)


def inspect_repository(path: Path, git: GitService | None = None) -> dict[str, Any]:
    git = git or GitService()
    root = git.repository_root(path.resolve())
    branch = git.run(root, "symbolic-ref", "--short", "-q", "HEAD", check=False).stdout.strip()
    remote = git.run(root, "config", "--get", "remote.origin.url", check=False).stdout.strip()
    markers = sorted(name for name in MARKERS if (root / name).is_file())
    markers.extend(sorted(item.name for item in root.glob("*.sln")))
    markers.extend(sorted(item.name for item in root.glob("*.csproj")))
    stacks: list[str] = []
    for marker, stack in (("pyproject.toml", "Python"), ("package.json", "JavaScript/Node.js"), ("Cargo.toml", "Rust"), ("go.mod", "Go"), ("pom.xml", "Java/JVM")):
        if marker in markers:
            stacks.append(stack)
    commands: list[str] = []
    if "pyproject.toml" in markers:
        commands += ["python -m pytest", "python -m ruff check ."]
    if "package.json" in markers:
        commands += ["npm test"]
    return {
        "repository_path": str(root), "remote_url": remote or None,
        "branch": branch or "detached", "detached": not bool(branch), "head": git.head(root),
        "clean": git.is_clean(root), "operating_system": platform.platform(),
        "python_version": platform.python_version(), "engine_version": __version__,
        "marker_files": markers, "likely_stack": stacks,
        "candidate_commands": [{"command": command, "status": "Candidate — requires owner confirmation"} for command in commands],
        "case_sensitive_paths": os.path.normcase("A") != os.path.normcase("a"),
        "python_executable": sys.executable,
    }
