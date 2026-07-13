"""Immutable, revisioned application Context Package snapshots."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from brain_engine.persistence import atomic_write_text, read_yaml, write_yaml


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_context(
    data_dir: Path, project_id: str, task: str, package: dict[str, Any], *,
    new_revision: bool = False,
) -> dict[str, Any]:
    root = data_dir.resolve() / "context-packages" / project_id
    index_path = root / "index.yaml"
    index = read_yaml(index_path) if index_path.exists() else {"project_id": project_id, "revisions": []}
    if index["revisions"] and not new_revision:
        raise ValueError("A frozen Context Package already exists; request an explicit new revision.")
    revision = len(index["revisions"]) + 1
    task_path = root / f"TASK-r{revision}.md"
    context_path = root / f"CONTEXT-r{revision}.yaml"
    metadata_path = root / f"snapshot-r{revision}.yaml"
    if any(path.exists() for path in (task_path, context_path, metadata_path)):
        raise ValueError("Refusing to overwrite an existing Context snapshot revision.")
    atomic_write_text(task_path, task)
    write_yaml(context_path, package)
    metadata = {
        "revision": revision, "frozen_at": datetime.now().astimezone().isoformat(),
        "task_path": task_path.name, "task_sha256": _hash(task_path),
        "context_path": context_path.name, "context_sha256": _hash(context_path),
    }
    write_yaml(metadata_path, metadata)
    index["revisions"].append(metadata)
    index["latest_revision"] = revision
    write_yaml(index_path, index)
    return metadata


def latest_context(data_dir: Path, project_id: str) -> tuple[dict[str, Any], str, Path]:
    root = data_dir.resolve() / "context-packages" / project_id
    index = read_yaml(root / "index.yaml")
    metadata = index["revisions"][-1]
    task_path = root / metadata["task_path"]
    context_path = root / metadata["context_path"]
    if _hash(task_path) != metadata["task_sha256"] or _hash(context_path) != metadata["context_sha256"]:
        raise ValueError("Frozen Context Package integrity check failed.")
    return metadata, task_path.read_text(encoding="utf-8"), context_path
