"""Immutable discovery revision storage and review actions."""

from datetime import datetime
import hashlib
from pathlib import Path
import re
from typing import Any

from brain_engine import __version__
from brain_engine.discovery.models import ScanLimits, ScanResult
from brain_engine.discovery.scanner import RepositoryScanner, SCANNER_VERSION
from brain_engine.experiment.git import GitService
from brain_engine.persistence import atomic_write_text, read_yaml, write_yaml


CONTROLLED = (
    "evidence.yaml", "findings.yaml", "proposals.yaml", "questions.yaml", "conflicts.yaml",
    "report.yaml", "report.md",
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DiscoveryService:
    def __init__(self, data_dir: Path, *, limits: ScanLimits | None = None) -> None:
        self.data_dir = data_dir.resolve()
        self.limits = limits or ScanLimits()

    def scan(self, repository: Path, project_id: str | None = None) -> dict[str, Any]:
        result = RepositoryScanner(self.limits).scan(repository)
        if project_id is None:
            project_id = hashlib.sha256(result.repository_path.encode("utf-8")).hexdigest()[:16]
        if re.fullmatch(r"[a-z0-9-]+", project_id) is None:
            raise ValueError("Invalid project ID.")
        root = self.data_dir / "discoveries" / project_id
        index_path = root / "index.yaml"
        index = read_yaml(index_path) if index_path.exists() else {"project_id": project_id, "revisions": []}
        revision = len(index["revisions"]) + 1
        revision_root = root / f"revision-{revision}"
        revision_root.mkdir(parents=True, exist_ok=False)
        sections = self._sections(result)
        for name in ("evidence", "findings", "proposals", "questions", "conflicts"):
            write_yaml(revision_root / f"{name}.yaml", {name: sections[name]})
        report = {key: value for key, value in sections.items()}
        write_yaml(revision_root / "report.yaml", report)
        atomic_write_text(revision_root / "report.md", self._markdown(project_id, revision, result, sections))
        artifact_hashes = {name: _hash(revision_root / name) for name in CONTROLLED}
        metadata = {
            "project_id": project_id, "revision": revision,
            "repository_path": result.repository_path, "repository_sha": result.repository_sha,
            "branch": result.branch, "detached": result.detached,
            "created_at": datetime.now().astimezone().isoformat(),
            "scanner_version": SCANNER_VERSION, "engine_version": __version__,
            "scan_limits": result.limits.to_dict(), "scanned_files": result.scanned_files,
            "scanned_bytes": result.scanned_bytes, "partial_analysis_warnings": result.warnings,
            "artifact_sha256": artifact_hashes,
        }
        write_yaml(revision_root / "metadata.yaml", metadata)
        entry = {
            "revision": revision, "repository_sha": result.repository_sha,
            "created_at": metadata["created_at"], "path": revision_root.name,
            "metadata_sha256": _hash(revision_root / "metadata.yaml"),
        }
        index["revisions"].append(entry)
        index["latest_revision"] = revision
        write_yaml(index_path, index)
        return self.load(project_id, revision)

    def load(self, project_id: str, revision: int | None = None) -> dict[str, Any]:
        root = self.data_dir / "discoveries" / project_id
        index = read_yaml(root / "index.yaml")
        entry = index["revisions"][-1] if revision is None else next(
            item for item in index["revisions"] if item["revision"] == revision
        )
        revision_root = root / entry["path"]
        metadata = read_yaml(revision_root / "metadata.yaml")
        if _hash(revision_root / "metadata.yaml") != entry["metadata_sha256"]:
            raise ValueError("Discovery metadata integrity check failed.")
        for name, expected in metadata["artifact_sha256"].items():
            if _hash(revision_root / name) != expected:
                raise ValueError(f"Discovery artifact integrity check failed: {name}.")
        report = read_yaml(revision_root / "report.yaml")
        reviews_path = revision_root / "reviews.yaml"
        report["reviews"] = read_yaml(reviews_path).get("reviews", []) if reviews_path.exists() else []
        review_by_proposal = {item["proposal_id"]: item for item in report["reviews"]}
        for proposal in report["proposals"]:
            if proposal["proposal_id"] in review_by_proposal:
                proposal["review_status"] = review_by_proposal[proposal["proposal_id"]]["action"]
        question_reviews_path = revision_root / "question-reviews.yaml"
        report["question_reviews"] = (
            read_yaml(question_reviews_path).get("reviews", [])
            if question_reviews_path.exists() else []
        )
        reviewed_questions = {item["question_id"]: item for item in report["question_reviews"]}
        for question in report["questions"]:
            if question["question_id"] in reviewed_questions:
                question["review_status"] = "answered"
                question["answer"] = reviewed_questions[question["question_id"]]["answer"]
        conflict_reviews_path = revision_root / "conflict-reviews.yaml"
        report["conflict_reviews"] = (
            read_yaml(conflict_reviews_path).get("reviews", [])
            if conflict_reviews_path.exists() else []
        )
        reviewed_conflicts = {item["conflict_id"]: item for item in report["conflict_reviews"]}
        for conflict in report["conflicts"]:
            if conflict["conflict_id"] in reviewed_conflicts:
                conflict["review_status"] = reviewed_conflicts[conflict["conflict_id"]]["action"]
        report.update({"metadata": metadata, "report_path": str(revision_root / "report.md")})
        try:
            report["stale"] = GitService().head(Path(metadata["repository_path"])) != metadata["repository_sha"]
        except Exception:
            report["stale"] = True
        return report

    def latest(self, project_id: str) -> dict[str, Any] | None:
        try:
            return self.load(project_id)
        except FileNotFoundError:
            return None

    def review(self, project_id: str, revision: int, proposal_id: str, action: str, *, title: str | None = None, content: str | None = None) -> dict[str, Any]:
        if action not in {"accept", "reject", "uncertain", "question"}:
            raise ValueError("Invalid review action.")
        root = self.data_dir / "discoveries" / project_id / f"revision-{revision}"
        source = read_yaml(root / "proposals.yaml")["proposals"]
        proposal = next((item for item in source if item["proposal_id"] == proposal_id), None)
        if proposal is None:
            raise ValueError("Proposal not found.")
        reviews_path = root / "reviews.yaml"
        reviews = read_yaml(reviews_path) if reviews_path.exists() else {"reviews": []}
        if any(item["proposal_id"] == proposal_id for item in reviews["reviews"]):
            raise ValueError("Proposal already reviewed in this immutable discovery revision.")
        review = {
            "proposal_id": proposal_id, "action": action,
            "title": title.strip() if title else proposal["title"],
            "content": content.strip() if content else proposal["content"],
            "reviewed_at": datetime.now().astimezone().isoformat(),
        }
        reviews["reviews"].append(review)
        write_yaml(reviews_path, reviews)
        return review

    def answer_question(
        self, project_id: str, revision: int, question_id: str, answer: str,
    ) -> dict[str, Any]:
        root = self.data_dir / "discoveries" / project_id / f"revision-{revision}"
        questions = read_yaml(root / "questions.yaml")["questions"]
        if not any(item["question_id"] == question_id for item in questions):
            raise ValueError("Question not found.")
        answer = answer.strip()
        if not answer:
            raise ValueError("A question answer is required; 'I do not know' is accepted.")
        target = root / "question-reviews.yaml"
        reviews = read_yaml(target) if target.exists() else {"reviews": []}
        if any(item["question_id"] == question_id for item in reviews["reviews"]):
            raise ValueError("Question already answered in this discovery revision.")
        review = {
            "question_id": question_id, "answer": answer,
            "reviewed_at": datetime.now().astimezone().isoformat(),
        }
        reviews["reviews"].append(review)
        write_yaml(target, reviews)
        return review

    def review_conflict(
        self, project_id: str, revision: int, conflict_id: str, action: str,
        selected_value: str = "",
    ) -> dict[str, Any]:
        if action not in {"select", "uncertain"}:
            raise ValueError("Invalid conflict review action.")
        root = self.data_dir / "discoveries" / project_id / f"revision-{revision}"
        conflicts = read_yaml(root / "conflicts.yaml")["conflicts"]
        if not any(item["conflict_id"] == conflict_id for item in conflicts):
            raise ValueError("Conflict not found.")
        if action == "select" and not selected_value.strip():
            raise ValueError("Selecting a conflict side requires a value.")
        target = root / "conflict-reviews.yaml"
        reviews = read_yaml(target) if target.exists() else {"reviews": []}
        if any(item["conflict_id"] == conflict_id for item in reviews["reviews"]):
            raise ValueError("Conflict already reviewed in this discovery revision.")
        review = {
            "conflict_id": conflict_id, "action": action,
            "selected_value": selected_value.strip() or None,
            "reviewed_at": datetime.now().astimezone().isoformat(),
        }
        reviews["reviews"].append(review)
        write_yaml(target, reviews)
        return review

    def create_reviewed_items(self, project_id: str, revision: int, brain: Path, *, confirmed: bool) -> list[Path]:
        from brain_engine.application.services.brain_service import BrainService

        if not confirmed:
            raise ValueError("Bulk creation requires explicit review confirmation.")
        root = self.data_dir / "discoveries" / project_id / f"revision-{revision}"
        reviews_path = root / "reviews.yaml"
        reviews = read_yaml(reviews_path).get("reviews", []) if reviews_path.exists() else []
        proposals = {item["proposal_id"]: item for item in read_yaml(root / "proposals.yaml")["proposals"]}
        created: list[Path] = []
        service = BrainService()
        existing_items = {item.id: item for item in service.list_items(brain)}
        for review in reviews:
            if review["action"] not in {"accept", "question"}:
                continue
            proposal = proposals[review["proposal_id"]]
            item_type = "question" if review["action"] == "question" else proposal["item_type"]
            item_id = ("question.discovery." if item_type == "question" else "discovery.") + review["proposal_id"].removeprefix("proposal-")
            content = review["content"] + "\n\nDiscovery evidence: " + ", ".join(proposal["evidence_refs"])
            metadata = {
                "id": item_id, "type": item_type, "title": review["title"],
                "origin": "discovery", "sources": proposal["evidence_refs"],
            }
            existing = existing_items.get(item_id)
            if existing:
                if existing.status != "proposed" or existing.metadata.get("origin") != "discovery":
                    raise ValueError(
                        f"Refusing to replace authoritative or non-discovery Item: {item_id}."
                    )
                created.append(service.update_item(brain, item_id, metadata, content))
            else:
                created.append(service.save_item(brain, metadata, content))
        return created

    @staticmethod
    def _sections(result: ScanResult) -> dict[str, Any]:
        return {
            "repository_sha": result.repository_sha,
            "observed_evidence": [item.to_dict() for item in result.evidence],
            "evidence": [item.to_dict() for item in result.evidence],
            "detected_facts": [item.to_dict() for item in result.findings],
            "findings": [item.to_dict() for item in result.findings],
            "inferred_proposals": [item.to_dict() for item in result.proposals],
            "proposals": [item.to_dict() for item in result.proposals],
            "unresolved_questions": [item.to_dict() for item in result.questions],
            "questions": [item.to_dict() for item in result.questions],
            "conflicts": [item.to_dict() for item in result.conflicts],
            "skipped_or_partial": result.skipped,
            "warnings": result.warnings,
        }

    @staticmethod
    def _markdown(project_id: str, revision: int, result: ScanResult, sections: dict[str, Any]) -> str:
        def safe(value: object) -> str:
            return (
                str(value).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace("`", "&#96;")
            )

        lines = [
            f"# Project Discovery Report — {safe(project_id)} revision {revision}", "",
            f"Repository SHA: `{safe(result.repository_sha)}`", "",
            "All findings and proposals are unapproved. Repository content was treated as untrusted and no discovered command was executed.", "",
        ]
        for heading, key in (
            ("Observed evidence", "evidence"), ("Detected facts", "findings"),
            ("Inferred proposals", "proposals"), ("Unresolved questions", "questions"),
            ("Conflicts", "conflicts"), ("Skipped or partially analyzed areas", "skipped_or_partial"),
        ):
            lines.extend([f"## {heading}", ""])
            values = sections[key]
            if not values:
                lines.extend(["None.", ""])
            else:
                for value in values:
                    label = value.get("source_path") or value.get("kind") or value.get("title") or value.get("uncertainty") or value.get("path") or value.get("conflict_id")
                    lines.append(f"- {safe(label)}: `{safe(value)}`")
                lines.append("")
        return "\n".join(lines)
