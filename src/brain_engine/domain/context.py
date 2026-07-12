"""Domain objects for deterministic Context Package generation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RequestPackage:
    task: str
    source: str = "cli"
    answers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "source": self.source,
            "answers": {key: self.answers[key] for key in sorted(self.answers)},
        }


@dataclass(frozen=True, slots=True)
class TaskClassification:
    intent: str
    domains: tuple[str, ...]
    risk: str

    def to_dict(self) -> dict[str, Any]:
        return {"intent": self.intent, "domains": list(self.domains), "risk": self.risk}


@dataclass(frozen=True, slots=True)
class QuestionResolution:
    question_id: str
    question_text: str
    severity: str
    status: str
    answer_mode: str
    answer_item_ids: tuple[str, ...]
    missing_answer_item_ids: tuple[str, ...]
    request_answer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "severity": self.severity,
            "status": self.status,
            "answer_mode": self.answer_mode,
            "answer_item_ids": list(self.answer_item_ids),
            "missing_answer_item_ids": list(self.missing_answer_item_ids),
            "request_answer": self.request_answer,
        }


@dataclass(frozen=True, slots=True)
class SelectedContextItem:
    item_id: str
    revision: int
    type: str
    tier: str
    content: str
    selection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "revision": self.revision,
            "type": self.type,
            "tier": self.tier,
            "content": self.content,
            "selection_reasons": list(self.selection_reasons),
        }


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    status: str
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
        }


@dataclass(frozen=True, slots=True)
class ContextPackage:
    schema_version: str
    request: RequestPackage
    classification: TaskClassification
    execution_policy: ExecutionPolicy
    question_resolutions: tuple[QuestionResolution, ...]
    critical_items: tuple[SelectedContextItem, ...] = field(default_factory=tuple)
    required_items: tuple[SelectedContextItem, ...] = field(default_factory=tuple)
    supporting_items: tuple[SelectedContextItem, ...] = field(default_factory=tuple)
    available_on_demand_items: tuple[SelectedContextItem, ...] = field(default_factory=tuple)
    selection_explanations: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request": self.request.to_dict(),
            "classification": self.classification.to_dict(),
            "execution_policy": self.execution_policy.to_dict(),
            "question_resolutions": [item.to_dict() for item in self.question_resolutions],
            "critical_items": [item.to_dict() for item in self.critical_items],
            "required_items": [item.to_dict() for item in self.required_items],
            "supporting_items": [item.to_dict() for item in self.supporting_items],
            "available_on_demand_items": [
                item.to_dict() for item in self.available_on_demand_items
            ],
            "selection_explanations": {
                key: list(self.selection_explanations[key])
                for key in sorted(self.selection_explanations)
            },
        }
