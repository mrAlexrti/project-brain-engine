"""Neutral evaluation scoring and locking."""

from datetime import datetime
from pathlib import Path
from typing import Any

from brain_engine.experiment.storage import load_state, save_state
from brain_engine.persistence import write_yaml

RUBRIC = {"functional_correctness": 30, "contracts_architecture": 20, "scope_discipline": 10, "verification_quality": 15, "unsupported_assumptions": 10, "maintainability": 10, "execution_efficiency": 5}


def lock_evaluation(root: Path, results: dict[str, dict[str, Any]]) -> None:
    state = load_state(root)
    if state["evaluation"]["locked"]:
        raise ValueError("Evaluation is already locked; create an explicit revision.")
    for result_name in ("result-1", "result-2"):
        score = results.get(result_name, {})
        categories = score.get("categories", {})
        evidence = score.get("evidence", {})
        for name, maximum in RUBRIC.items():
            value = categories.get(name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
                raise ValueError(f"{result_name} {name} must be an integer from 0 to {maximum}.")
            if not str(evidence.get(name, "")).strip():
                raise ValueError(f"Written evidence is required for {result_name} {name}.")
        raw = sum(categories.values())
        cap = score.get("critical_failure_cap")
        if cap not in (None, 20, 40, 50):
            raise ValueError("Critical failure cap must be 20, 40, 50, or omitted.")
        score["total"] = min(raw, cap) if cap else raw
    timestamp = datetime.now().astimezone().isoformat()
    write_yaml(root / "evidence" / "evaluation" / "locked-scores.yaml", {"locked_at": timestamp, "results": results})
    state["evaluation"].update({"locked": True, "locked_at": timestamp, "scores": results})
    save_state(root, state)


def reveal_treatment(root: Path) -> dict[str, Any]:
    state = load_state(root)
    if not state["evaluation"]["locked"]:
        raise ValueError("Treatment cannot be revealed before evaluation is locked.")
    mapping = __import__("yaml").safe_load((root / "evidence" / "private" / "treatment-map.yaml").read_text(encoding="utf-8"))
    state["evaluation"]["treatment_revealed_at"] = datetime.now().astimezone().isoformat()
    save_state(root, state)
    return mapping
