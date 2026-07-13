"""Neutral Git evidence capture and conservative verification execution."""

import hashlib
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from brain_engine.experiment.git import GitService
from brain_engine.persistence import atomic_write_text, write_yaml

MAX_CAPTURED_FILE_BYTES = 256 * 1024
ALLOWED_DIRECT = {
    "pytest": {None},
    "ruff": {"check", "format"},
    "cargo": {"test", "check"},
    "go": {"test"},
    "dotnet": {"test"},
}
MUTATING_OPTIONS = {
    "--fix", "--unsafe-fixes", "--fix-only", "--write", "--update", "--bless",
    "--accept", "--overwrite", "--in-place", "--update-snapshots", "--snapshot-update",
    "--record", "--rewrite", "-w",
}


def now() -> str:
    return datetime.now().astimezone().isoformat()


def capture_evidence(root: Path, workspace: Path, result_name: str, baseline: str, metadata: dict[str, Any]) -> Path:
    git = GitService()
    destination = root / "evidence" / result_name
    destination.mkdir(parents=True, exist_ok=False)
    status = git.run(workspace, "status", "--porcelain=v1").stdout
    tracked_changed = git.run(workspace, "diff", "--name-only", baseline).stdout.splitlines()
    untracked_names = sorted(
        name for name in git.run(workspace, "ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0") if name
    )
    changed = "\n".join(sorted(set(tracked_changed + untracked_names)))
    if changed:
        changed += "\n"
    stat = git.run(workspace, "diff", "--stat", baseline).stdout
    numstat = git.run(workspace, "diff", "--numstat", baseline).stdout
    check = git.run(workspace, "diff", "--check", baseline, check=False)
    patch = git.run(workspace, "diff", "--binary", baseline).stdout
    untracked = _capture_untracked(workspace, destination, git)
    values = {
        "baseline-sha.txt": baseline + "\n", "final-head-sha.txt": git.head(workspace) + "\n",
        "git-status.txt": status, "changed-files.txt": changed, "diff-stat.txt": stat,
        "diff-numstat.txt": numstat, "diff-check.txt": check.stdout + check.stderr,
        "changes.patch": patch, "started-at.txt": str(metadata.get("started_at", "")) + "\n",
        "finished-at.txt": str(metadata.get("finished_at", "")) + "\n",
        "elapsed.txt": str(metadata.get("elapsed_seconds", 0)) + "\n",
        "permission-prompts.txt": str(metadata.get("permission_prompts", 0)) + "\n",
        "clarification-questions.txt": str(metadata.get("clarification_questions", 0)) + "\n",
        "corrective-iterations.txt": str(metadata.get("corrective_iterations", 0)) + "\n",
        "protocol-deviations.txt": str(metadata.get("protocol_deviations", "")) + "\n",
        "agent-final-report.txt": str(metadata.get("final_report", "")),
        "verification-results.md": str(metadata.get("verification_results", "Not run.\n")),
    }
    for name, text in values.items():
        atomic_write_text(destination / name, text)
    atomic_write_text(destination / "patch-sha256.txt", hashlib.sha256(patch.encode()).hexdigest() + "\n")
    write_yaml(destination / "untracked-files.yaml", {"files": untracked})
    write_yaml(destination / "agent-metadata.yaml", {key: metadata.get(key) for key in ("agent_product", "agent_version", "model", "reasoning_setting", "network_policy", "permission_policy")})
    _write_evidence_manifest(destination)
    return destination


def _write_evidence_manifest(destination: Path) -> None:
    target = destination / "evidence-manifest-sha256.txt"
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(destination).as_posix()}"
        for path in sorted(destination.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file() and not path.is_symlink() and path != target
    ]
    atomic_write_text(target, "\n".join(lines) + "\n")


def _capture_untracked(workspace: Path, destination: Path, git: GitService) -> list[dict[str, Any]]:
    """Inventory untracked files deterministically and capture only bounded UTF-8 regular files."""
    raw = git.run(workspace, "ls-files", "--others", "--exclude-standard", "-z").stdout
    names = sorted(name for name in raw.split("\0") if name)
    inventory: list[dict[str, Any]] = []
    base = workspace.resolve()
    capture_root = destination / "untracked-files"
    for name in names:
        source = base / name
        path = source.resolve()
        entry: dict[str, Any] = {"path": Path(name).as_posix(), "captured": False}
        try:
            path.relative_to(base)
            if source.is_symlink():
                link = os.readlink(source).encode("utf-8", errors="surrogatepass")
                entry.update({
                    "size": len(link), "sha256": hashlib.sha256(link).hexdigest(),
                    "reason": "symbolic link content is not captured",
                })
            elif not path.is_file():
                entry["reason"] = "not a regular file"
            else:
                content = path.read_bytes()
                entry.update({"size": len(content), "sha256": hashlib.sha256(content).hexdigest()})
                if len(content) > MAX_CAPTURED_FILE_BYTES:
                    entry["reason"] = "exceeds safe capture limit"
                elif b"\0" in content:
                    entry["reason"] = "binary content"
                else:
                    content.decode("utf-8")
                    target = capture_root / Path(name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
                    entry["captured"] = True
        except (OSError, UnicodeError, ValueError) as exc:
            entry["reason"] = f"not safely capturable: {type(exc).__name__}"
        inventory.append(entry)
    return inventory


def _verification_shape(command: list[str]) -> tuple[str, str | None]:
    executable = Path(command[0]).name.casefold()
    if executable.endswith(".exe") or executable.endswith(".cmd"):
        executable = executable.rsplit(".", 1)[0]
    arguments = command[1:]
    if executable in {"python", "python3", "py"}:
        if len(arguments) < 2 or arguments[0] != "-m":
            raise ValueError("Python verification must use an allowed -m module.")
        module = arguments[1].casefold()
        if module == "pytest":
            return "pytest", None
        if module == "ruff" and len(arguments) >= 3:
            return "ruff", arguments[2].casefold()
        raise ValueError("Python verification module or Ruff subcommand is not allowed.")
    subcommand = next((arg.casefold() for arg in arguments if not arg.startswith("-")), None)
    return executable, subcommand


def validate_verification_command(workspace: Path, command: list[str]) -> None:
    if not command or not command[0].strip():
        raise ValueError("Verification command is empty.")
    executable = Path(command[0])
    if executable.parent != Path("."):
        resolved = (workspace.resolve() / executable).resolve() if not executable.is_absolute() else executable.resolve()
        try:
            resolved.relative_to(workspace.resolve())
        except ValueError as exc:
            raise ValueError("Verification executable must be on PATH or inside the workspace.") from exc
    name, subcommand = _verification_shape(command)
    allowed = ALLOWED_DIRECT.get(name)
    if allowed is None or subcommand not in allowed:
        raise ValueError(f"Verification executable/subcommand is not allowed: {name} {subcommand or ''}".rstrip())
    normalized = {argument.casefold().split("=", 1)[0] for argument in command[1:]}
    if normalized & MUTATING_OPTIONS:
        raise ValueError("Mutating options are not allowed in verification commands.")
    if name == "ruff" and subcommand == "format" and "--check" not in normalized:
        raise ValueError("ruff format is allowed only with --check.")


def run_verification(workspace: Path, command: list[str], timeout: int) -> dict[str, Any]:
    validate_verification_command(workspace, command)
    started = time.monotonic()
    completed = subprocess.run(command, cwd=workspace.resolve(), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, shell=False)
    return {"command": command, "exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "duration_seconds": round(time.monotonic() - started, 3)}
