"""Explicit application-domain models for project discovery."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ScanLimits:
    max_files: int = 250
    max_tree_entries: int = 5000
    max_depth: int = 4
    max_file_bytes: int = 256 * 1024
    max_excerpt_bytes: int = 600
    max_total_bytes: int = 2 * 1024 * 1024

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    repository_sha: str
    source_path: str
    source_locator: str
    detector_name: str
    detector_version: str
    source_sha256: str | None = None
    excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    kind: str
    normalized_value: Any
    confidence: str
    evidence_refs: tuple[str, ...]
    explanation: str
    review_status: str = "unreviewed"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_refs"] = list(self.evidence_refs)
        return value


@dataclass(frozen=True, slots=True)
class Proposal:
    proposal_id: str
    item_type: str
    title: str
    content: str
    evidence_refs: tuple[str, ...]
    status: str = "proposed"
    review_status: str = "unreviewed"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_refs"] = list(self.evidence_refs)
        return value


@dataclass(frozen=True, slots=True)
class Question:
    question_id: str
    uncertainty: str
    reason: str
    evidence_refs: tuple[str, ...] = ()
    suggested_answers: tuple[str, ...] = ()
    review_status: str = "unresolved"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_refs"] = list(self.evidence_refs)
        value["suggested_answers"] = [*self.suggested_answers, "I do not know"]
        return value


@dataclass(frozen=True, slots=True)
class Conflict:
    conflict_id: str
    kind: str
    sides: tuple[dict[str, Any], ...]
    explanation: str
    review_status: str = "unresolved"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["sides"] = list(self.sides)
        return value


@dataclass(slots=True)
class ScanResult:
    repository_path: str
    repository_sha: str
    branch: str
    detached: bool
    limits: ScanLimits
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    proposals: list[Proposal] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    scanned_files: int = 0
    scanned_bytes: int = 0
