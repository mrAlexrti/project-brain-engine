"""Experiment YAML storage and safe path resolution."""

from pathlib import Path
from typing import Any
from datetime import datetime

from brain_engine.persistence import read_yaml, write_yaml

STATE_FILE = "experiment.yaml"


def load_state(root: Path) -> dict[str, Any]:
    return read_yaml(root.resolve() / STATE_FILE)


def save_state(root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now().astimezone().isoformat()
    write_yaml(root.resolve() / STATE_FILE, state)


def safe_child(root: Path, relative: str) -> Path:
    base = root.resolve()
    target = (base / relative).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError("Path escapes the experiment root.") from exc
    return target
