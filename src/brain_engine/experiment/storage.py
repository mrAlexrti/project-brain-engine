"""Experiment YAML storage and safe path resolution."""

from pathlib import Path
from typing import Any
from datetime import datetime

from brain_engine.persistence import read_yaml, write_yaml

STATE_FILE = "experiment.yaml"


def load_state(root: Path) -> dict[str, Any]:
    state = read_yaml(root.resolve() / STATE_FILE)
    state.setdefault("protocol_quality", {
        "classification": "pilot", "deviations": ["legacy record without protocol-quality data"],
        "duration_comparison_valid": True,
    })
    for result in state.get("results", {}).values():
        legacy = result.get("permission_prompts", 0)
        result.setdefault("setup_prompts", 0)
        result.setdefault("task_permission_prompts", legacy)
    return state


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
