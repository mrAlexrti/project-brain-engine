"""Strict argument-list Git orchestration."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GitResult:
    stdout: str
    stderr: str
    returncode: int


class GitService:
    def run(self, cwd: Path, *args: str, timeout: int = 60, check: bool = True) -> GitResult:
        completed = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, shell=False,
        )
        result = GitResult(completed.stdout, completed.stderr, completed.returncode)
        if check and completed.returncode:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise GitError(f"git {' '.join(args)} failed: {detail}")
        return result

    def repository_root(self, path: Path) -> Path:
        return Path(self.run(path, "rev-parse", "--show-toplevel").stdout.strip()).resolve()

    def head(self, path: Path) -> str:
        return self.run(path, "rev-parse", "HEAD").stdout.strip()

    def is_clean(self, path: Path) -> bool:
        return not self.run(path, "status", "--porcelain").stdout.strip()

    def add_worktree(self, repository: Path, destination: Path, sha: str) -> None:
        self.run(repository, "worktree", "add", "--detach", str(destination), sha, timeout=180)

    def remove_worktree(self, repository: Path, destination: Path) -> None:
        self.run(repository, "worktree", "remove", "--force", str(destination), check=False)


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
