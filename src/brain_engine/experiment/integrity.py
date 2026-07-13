"""Integrity manifest generation."""

import hashlib
from pathlib import Path

from brain_engine.persistence import atomic_write_text


def generate_manifest(root: Path) -> Path:
    target = root / "evidence" / "integrity-manifest-sha256.txt"
    lines = []
    files = [root / name for name in (
        "experiment.yaml", "TASK.md", "GROUND_TRUTH.md", "DO_NOT_PUBLISH.md",
        "PROJECT_INTAKE.md",
    )]
    for directory in ("run-package-1", "run-package-2", "evidence"):
        controlled = root / directory
        if controlled.is_dir():
            files.extend(controlled.rglob("*"))
    for path in sorted(files, key=lambda item: item.as_posix()):
        if path.is_file() and not path.is_symlink() and path != target:
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    atomic_write_text(target, "\n".join(lines) + "\n")
    return target
