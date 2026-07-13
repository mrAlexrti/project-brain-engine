"""Application-independent controlled experiment orchestration."""

import hashlib
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from brain_engine import __version__
from brain_engine.context import build_context
from brain_engine.domain import RequestPackage
from brain_engine.experiment.evidence import capture_evidence, now
from brain_engine.experiment.evaluation import RUBRIC
from brain_engine.experiment.git import GitError, GitService, is_within
from brain_engine.experiment.integrity import generate_manifest
from brain_engine.experiment.metadata import inspect_repository
from brain_engine.experiment.storage import load_state, save_state
from brain_engine.persistence import atomic_write_bytes, atomic_write_text, write_json, write_yaml
from brain_engine.validation import validate_path


class ExperimentError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExperimentService:
    def __init__(self, git: GitService | None = None) -> None:
        self.git = git or GitService()

    def initialize(
        self, repository: Path, output: Path, task: str, ground_truth: str, brain_path: Path,
        *, privacy: str = "private", controls: dict[str, Any] | None = None,
        allow_existing_brain: bool = False,
        frozen_context_path: Path | None = None,
        frozen_context_revision: int = 1,
    ) -> Path:
        repository = self.git.repository_root(repository)
        output = output.resolve()
        if privacy not in {"private", "anonymized-results-only", "public"}:
            raise ExperimentError("Invalid privacy mode.")
        if isinstance(frozen_context_revision, bool) or frozen_context_revision < 1:
            raise ExperimentError("Context Package revision must be a positive integer.")
        if not self.git.is_clean(repository):
            raise ExperimentError("Source repository must have a clean working tree.")
        if is_within(output, repository):
            raise ExperimentError("Experiment output must be outside the source repository.")
        if output.exists():
            raise ExperimentError(f"Refusing to overwrite existing experiment directory: {output}")
        validation = validate_path(brain_path)
        if not validation.success:
            raise ExperimentError("Brain validation must pass before experiment creation.")
        baseline = self.git.head(repository)
        created_worktrees: list[Path] = []
        try:
            output.mkdir(parents=True)
            for relative in ("run-package-1", "run-package-2", "evidence/baseline", "evidence/context-package", "evidence/evaluation", "evidence/private"):
                (output / relative).mkdir(parents=True)
            workspaces = [output / "workspace-1", output / "workspace-2", output / "workspace-context"]
            for workspace in workspaces:
                self.git.add_worktree(repository, workspace, baseline)
                created_worktrees.append(workspace)
            if any(self.git.head(workspace) != baseline for workspace in workspaces):
                raise ExperimentError("Created worktree HEAD values do not match the baseline.")
            baseline_has_brain = (repository / ".brain").exists()
            if baseline_has_brain and not allow_existing_brain:
                raise ExperimentError("Frozen baseline already contains .brain; explicit documentation is required.")
            for workspace in workspaces[:2]:
                if (workspace / ".brain").exists() and not baseline_has_brain:
                    raise ExperimentError("Brain isolation failed in an agent workspace.")
            context_brain = output / "workspace-context" / ".brain"
            if context_brain.exists():
                shutil.rmtree(context_brain)
            shutil.copytree(brain_path.resolve(), context_brain)
            task_path = output / "TASK.md"
            atomic_write_text(task_path, task)
            task_hash = sha256_file(task_path)
            if frozen_context_path is None:
                package = build_context(RequestPackage(task, source="experiment"), context_brain)
                package_dict = package.to_dict()
                package_dict["generation"] = {"engine_version": __version__, "generated_at": now(), "task_sha256": task_hash, "brain_validation_errors": 0}
                package_bytes = yaml.safe_dump(
                    package_dict, sort_keys=False, allow_unicode=True,
                ).encode("utf-8")
            else:
                package_bytes = frozen_context_path.resolve().read_bytes()
                package_dict = yaml.safe_load(package_bytes)
                if not isinstance(package_dict, dict):
                    raise ExperimentError("Frozen Context Package must contain a YAML mapping.")
                frozen_task = package_dict.get("request", {}).get("task")
                if frozen_task != task:
                    raise ExperimentError("Frozen Context Package task does not match TASK.md.")
            atomic_write_text(output / "GROUND_TRUTH.md", "# Evaluator-only Ground Truth\n\n" + ground_truth.rstrip() + "\n")
            atomic_write_text(output / "DO_NOT_PUBLISH.md", "Raw evidence may contain private code, rules, paths, and identities.\n")
            atomic_write_text(output / "PROJECT_INTAKE.md", "# Experiment Project Intake\n\nSee private local metadata for source repository details.\n")
            atomic_write_bytes(
                output / "evidence" / "context-package" / "context-package.yaml", package_bytes,
            )
            write_json(output / "evidence" / "context-package" / "context-package.json", package_dict)
            package_hash = sha256_file(output / "evidence" / "context-package" / "context-package.yaml")
            atomic_write_text(output / "evidence" / "context-package" / "sha256.txt", package_hash + "\n")
            treatment_result = secrets.choice(("result-1", "result-2"))
            run_order = list(("result-1", "result-2"))
            if secrets.randbelow(2):
                run_order.reverse()
            mapping = {"context_result": treatment_result, "created_at": now()}
            write_yaml(output / "evidence" / "private" / "treatment-map.yaml", mapping)
            write_yaml(output / "evidence" / "private" / "local-source.yaml", {"source_repository": str(repository)})
            for index, result_name in enumerate(run_order, 1):
                package_dir = output / f"run-package-{index}"
                shutil.copy2(output / "TASK.md", package_dir / "TASK.md")
                workspace_name = "workspace-1" if result_name == "result-1" else "workspace-2"
                prompt = self._prompt(workspace_name, controls or {})
                atomic_write_text(package_dir / "RUN_INSTRUCTIONS.md", prompt)
                if result_name == treatment_result:
                    shutil.copy2(output / "evidence" / "context-package" / "context-package.yaml", package_dir / "CONTEXT.yaml")
            created_at = now()
            inspected = inspect_repository(repository, self.git)
            repository_metadata = {
                key: inspected[key] for key in (
                    "remote_url", "branch", "detached", "head", "clean", "marker_files",
                    "likely_stack", "case_sensitive_paths",
                )
            }
            environment_metadata = {
                key: inspected[key] for key in (
                    "operating_system", "python_version", "python_executable", "engine_version",
                )
            }
            comparison = "contaminated-pilot" if baseline_has_brain else "clean-ab"
            state: dict[str, Any] = {
                "schema_version": "1.0", "experiment_id": output.name, "created_at": created_at,
                "updated_at": created_at, "privacy": {"mode": privacy},
                "repository": {"baseline_sha": baseline, "source_path": "evidence/private/local-source.yaml", "baseline_includes_brain": baseline_has_brain, **repository_metadata},
                "environment": environment_metadata,
                "project_metadata": {"candidate_commands": inspected["candidate_commands"]},
                "comparison": {"classification": comparison, "reportable_as_clean": not baseline_has_brain},
                "protocol_quality": {
                    "classification": "pilot" if baseline_has_brain else "compliant",
                    "deviations": (["baseline includes pre-existing Brain"] if baseline_has_brain else []),
                    "duration_comparison_valid": True,
                },
                "task": {"path": "TASK.md", "frozen": True, "sha256": task_hash},
                "brain": {"workspace": "workspace-context/.brain", "validation_passed": True, "proposed_items": sum(i.status == "proposed" for i in validation.items), "approved_items": sum(i.status == "approved" for i in validation.items)},
                "context_package": {"path": "evidence/context-package/context-package.yaml", "frozen": True, "sha256": package_hash, "revision": frozen_context_revision},
                "controls": controls or {},
                "workspaces": {"result-1": "workspace-1", "result-2": "workspace-2", "context": "workspace-context"},
                "run_order": run_order,
                "results": {"result-1": {"state": "ready"}, "result-2": {"state": "ready"}},
                "evaluation": {"package_state": "pending", "locked": False, "treatment_revealed_at": None},
                "integrity": {"finalized": False},
            }
            save_state(output, state)
            return output
        except BaseException as exc:
            for workspace in reversed(created_worktrees):
                self.git.remove_worktree(repository, workspace)
            if output.exists():
                shutil.rmtree(output)
            if isinstance(exc, ExperimentError):
                raise
            if isinstance(exc, GitError):
                raise ExperimentError(str(exc)) from exc
            raise

    @staticmethod
    def _prompt(workspace: str, controls: dict[str, Any]) -> str:
        return (
            "# Neutral Run Instructions\n\nExecute the canonical task in the designated workspace.\n\n"
            f"Workspace: `{workspace}`\n\nTime limit: {controls.get('time_limit', 'operator-defined')}\n\n"
            f"Permission policy: {controls.get('permission_policy', 'operator-defined')}\n\n"
            f"Network policy: {controls.get('network_policy', 'operator-defined')}\n\n"
            "Do not commit, push, deploy, access production, or perform destructive operations.\n\n"
            "Final report: summary; files changed; verification performed; remaining risks; assumptions.\n"
        )

    def status(self, root: Path) -> tuple[dict[str, Any], bool]:
        state = load_state(root)
        baseline = state["repository"]["baseline_sha"]
        heads: dict[str, str | None] = {}
        clean: dict[str, bool] = {}
        consistent = True
        for name, relative in state["workspaces"].items():
            path = root / relative
            try:
                heads[name] = self.git.head(path)
                clean[name] = self.git.is_clean(path)
                consistent &= heads[name] == baseline
            except GitError:
                heads[name], clean[name], consistent = None, False, False
        checks = self._checks(root, state)
        consistent &= all(
            passed for name, passed in checks.items() if name != "evidence_complete"
        )
        run_order = state.get("run_order", ["result-1", "result-2"])
        packages = {
            result_name: str((root.resolve() / f"run-package-{run_order.index(result_name) + 1}"))
            for result_name in ("result-1", "result-2")
        }
        operator = {
            result_name: {
                "workspace_path": str((root.resolve() / state["workspaces"][result_name])),
                "run_package_path": packages[result_name],
                "prepared_prompt": self._prepared_prompt(
                    root.resolve() / state["workspaces"][result_name], Path(packages[result_name]),
                ),
            }
            for result_name in ("result-1", "result-2")
        }
        public = {
            **state, "workspace_heads": heads, "workspace_clean": clean, "checks": checks,
            "consistent": consistent, "operator": operator,
        }
        public.pop("run_order", None)
        return public, consistent

    @staticmethod
    def _prepared_prompt(workspace: Path, package: Path) -> str:
        return (
            "Execute the neutral run package without inferring or discussing treatment assignment.\n\n"
            f"Workspace: {workspace}\n"
            f"Neutral run package: {package}\n\n"
            "Read TASK.md and RUN_INSTRUCTIONS.md from that package, then perform the task only "
            "in the designated workspace. Do not start work in the package directory."
        )

    def start_run(self, root: Path, result_name: str) -> None:
        state = load_state(root)
        result = state["results"][result_name]
        if result["state"] != "ready":
            raise ExperimentError("Run is not ready to start.")
        concurrent = [
            name for name, other in state["results"].items()
            if name != result_name and other["state"] == "running"
        ]
        if concurrent:
            deviation = f"concurrent runs: {result_name} overlapped {concurrent[0]}"
            quality = state["protocol_quality"]
            quality["classification"] = "deviated"
            quality["duration_comparison_valid"] = False
            if deviation not in quality["deviations"]:
                quality["deviations"].append(deviation)
            for name in [result_name, *concurrent]:
                existing = state["results"][name].get("protocol_deviations", "").strip()
                state["results"][name]["protocol_deviations"] = "\n".join(
                    value for value in (existing, deviation) if value
                )
        result.update({"state": "running", "started_at": now()})
        save_state(root, state)

    def finish_run(self, root: Path, result_name: str, metadata: dict[str, Any]) -> None:
        state = load_state(root)
        result = state["results"][result_name]
        if result["state"] != "running":
            raise ExperimentError("Run is not running.")
        finished = now()
        started = datetime.fromisoformat(result["started_at"])
        elapsed = (datetime.fromisoformat(finished) - started).total_seconds()
        result.update(metadata)
        setup_prompts = metadata.get("setup_prompts", result.get("setup_prompts", 0))
        task_prompts = metadata.get(
            "task_permission_prompts", metadata.get("permission_prompts", 0),
        )
        result.update({
            "setup_prompts": setup_prompts,
            "task_permission_prompts": task_prompts,
            "permission_prompts": task_prompts,
        })
        if str(result.get("protocol_deviations", "")).strip():
            state["protocol_quality"]["classification"] = "deviated"
            for line in str(result["protocol_deviations"]).splitlines():
                if line.strip() and line.strip() not in state["protocol_quality"]["deviations"]:
                    state["protocol_quality"]["deviations"].append(line.strip())
        result.update({"state": "finished", "finished_at": finished, "elapsed_seconds": elapsed})
        save_state(root, state)

    def capture(self, root: Path, result_name: str) -> Path:
        state = load_state(root)
        result = state["results"][result_name]
        if result["state"] != "finished":
            raise ExperimentError("Finish the run before capturing evidence.")
        destination = capture_evidence(root, root / state["workspaces"][result_name], result_name, state["repository"]["baseline_sha"], result)
        result["state"] = "captured"
        result["evidence_path"] = str(destination.relative_to(root)).replace("\\", "/")
        result["evidence_manifest_sha256"] = sha256_file(
            destination / "evidence-manifest-sha256.txt"
        )
        save_state(root, state)
        return destination

    def finalize(self, root: Path) -> Path:
        state = load_state(root)
        if any(state["results"][name]["state"] != "captured" for name in ("result-1", "result-2")):
            raise ExperimentError("Both run evidence sets are required.")
        if not state["evaluation"]["locked"]:
            raise ExperimentError("Evaluation must be locked.")
        if not state["evaluation"]["treatment_revealed_at"]:
            raise ExperimentError("Treatment mapping must be revealed after locking.")
        checks = self._checks(root, state)
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise ExperimentError("Finalization integrity checks failed: " + ", ".join(failed))
        private_map = root / "evidence" / "private" / "treatment-map.yaml"
        evaluator = root / "evidence" / "evaluation" / "neutral-evaluator-package"
        if evaluator.exists() and any(evaluator.iterdir()):
            raise ExperimentError("Refusing to merge into a pre-existing evaluator package.")
        evaluator.mkdir(parents=True, exist_ok=True)
        for name in ("TASK.md", "GROUND_TRUTH.md"):
            shutil.copy2(root / name, evaluator / name)
        for name in ("result-1", "result-2"):
            shutil.copytree(root / "evidence" / name, evaluator / name, dirs_exist_ok=True)
        if not self._evaluator_neutral(evaluator):
            raise ExperimentError("Evaluator package is not treatment-neutral.")
        scores = state["evaluation"]["scores"]
        mapping = yaml.safe_load(private_map.read_text(encoding="utf-8"))
        heading = "# Final Evaluation"
        if state.get("comparison", {}).get("classification") == "contaminated-pilot":
            heading += " (Contaminated Pilot — Not a Clean A/B Result)"
        lines = [
            heading, "",
            f"- Comparison classification: {state['comparison']['classification']}",
            f"- Reportable as clean A/B: {state['comparison']['reportable_as_clean']}",
            f"- Protocol quality: {state['protocol_quality']['classification']}",
            f"- Duration comparison valid: {state['protocol_quality']['duration_comparison_valid']}",
            f"- Treatment result after reveal: {mapping['context_result']}",
        ]
        for name in ("result-1", "result-2"):
            score = scores[name]
            result = state["results"][name]
            lines.extend(["", f"## {name}", "", f"- Total: {score['total']}/100"])
            cap = score.get("critical_failure_cap")
            lines.append(f"- Critical-failure cap: {cap if cap is not None else 'none'}")
            lines.append(f"- Unsupported assumptions: {score.get('unsupported_assumptions') or 'none'}")
            lines.append(f"- Protocol deviations: {result.get('protocol_deviations') or 'none'}")
            lines.append(f"- Operator notes: {result.get('operator_notes') or 'none'}")
            lines.extend(["", "### Category scores and evidence", ""])
            for category, maximum in RUBRIC.items():
                lines.extend([
                    f"- {category}: {score['categories'][category]}/{maximum}",
                    f"  - Evidence: {score['evidence'][category]}",
                ])
        final = "\n".join(lines) + "\n"
        final_path = root / "evidence" / "evaluation" / "final-evaluation.md"
        atomic_write_text(final_path, final)
        atomic_write_text(root / "evidence" / "evaluation" / "final-evaluation-sha256.txt", hashlib.sha256(final.encode()).hexdigest() + "\n")
        atomic_write_text(root / "evidence" / "private" / "full-experiment-summary.md", final + f"\nContext result: {mapping['context_result']}\n")
        state["integrity"]["finalized"] = True
        state["integrity"]["finalized_at"] = now()
        save_state(root, state)
        return generate_manifest(root)

    def _checks(self, root: Path, state: dict[str, Any]) -> dict[str, bool]:
        task = root / state["task"]["path"]
        context = root / state["context_package"]["path"]
        baseline_has_brain = bool(state["repository"].get("baseline_includes_brain"))
        if baseline_has_brain:
            try:
                isolation = all(
                    not self.git.run(
                        root / state["workspaces"][name], "status", "--porcelain", "--", ".brain",
                    ).stdout.strip()
                    for name in ("result-1", "result-2")
                )
            except GitError:
                isolation = False
        else:
            isolation = all(
                not (root / state["workspaces"][name] / ".brain").exists()
                for name in ("result-1", "result-2")
            )
        evidence_complete = all(
            state["results"][name].get("state") == "captured"
            and self._evidence_complete(
                root / "evidence" / name,
                state["results"][name].get("evidence_manifest_sha256"),
            )
            for name in ("result-1", "result-2")
        )
        evaluator = root / "evidence" / "evaluation" / "neutral-evaluator-package"
        return {
            "task_hash": task.is_file() and sha256_file(task) == state["task"]["sha256"],
            "context_hash": context.is_file() and sha256_file(context) == state["context_package"]["sha256"],
            "brain_isolation": isolation,
            "evidence_complete": evidence_complete,
            "evaluator_package_neutral": not evaluator.exists() or self._evaluator_neutral(evaluator),
            "comparison_classified": (
                state.get("comparison", {}).get("reportable_as_clean") is True
                or state.get("comparison", {}).get("classification") == "contaminated-pilot"
            ),
        }

    @staticmethod
    def _evidence_complete(path: Path, expected_manifest_hash: str | None) -> bool:
        required = {
            "baseline-sha.txt", "final-head-sha.txt", "git-status.txt", "changed-files.txt",
            "changes.patch", "patch-sha256.txt", "untracked-files.yaml", "agent-metadata.yaml",
            "started-at.txt", "finished-at.txt", "agent-final-report.txt",
            "evidence-manifest-sha256.txt",
        }
        if not path.is_dir() or not all((path / name).is_file() for name in required):
            return False
        manifest = path / "evidence-manifest-sha256.txt"
        if not expected_manifest_hash or sha256_file(manifest) != expected_manifest_hash:
            return False
        manifested: set[str] = set()
        for line in manifest.read_text(encoding="utf-8").splitlines():
            try:
                expected, relative = line.split("  ", 1)
                artifact = (path / relative).resolve()
                artifact.relative_to(path.resolve())
            except ValueError:
                return False
            if not artifact.is_file() or artifact.is_symlink() or sha256_file(artifact) != expected:
                return False
            manifested.add(Path(relative).as_posix())
        actual = {
            item.relative_to(path).as_posix() for item in path.rglob("*")
            if item.is_file() and not item.is_symlink() and item != manifest
        }
        if manifested != actual:
            return False
        if sha256_file(path / "changes.patch") != (path / "patch-sha256.txt").read_text(encoding="utf-8").strip():
            return False
        inventory = yaml.safe_load((path / "untracked-files.yaml").read_text(encoding="utf-8"))
        if not isinstance(inventory, dict) or not isinstance(inventory.get("files"), list):
            return False
        for entry in inventory["files"]:
            if not isinstance(entry, dict) or not {
                "path", "captured", "size", "sha256",
            } <= entry.keys():
                return False
            if entry["captured"]:
                captured = path / "untracked-files" / entry["path"]
                if not captured.is_file() or sha256_file(captured) != entry.get("sha256"):
                    return False
        return True

    @staticmethod
    def _evaluator_neutral(path: Path) -> bool:
        if not path.exists():
            return True
        forbidden_names = {"treatment-map.yaml", "local-source.yaml", "full-experiment-summary.md", "CONTEXT.yaml"}
        allowed_top_level = {"TASK.md", "GROUND_TRUTH.md", "result-1", "result-2"}
        return (
            all(item.name not in forbidden_names for item in path.rglob("*"))
            and all(item.name in allowed_top_level for item in path.iterdir())
        )
