"""Deterministic question-driven Context Package builder."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brain_engine.context.classifier import classify_task, task_tokens
from brain_engine.domain import BrainItem
from brain_engine.domain.context import (
    ContextPackage,
    ExecutionPolicy,
    QuestionResolution,
    RequestPackage,
    SelectedContextItem,
)
from brain_engine.validation import validate_path


class ContextBuildError(Exception):
    """Known routing metadata cannot be interpreted safely."""


class BrainContentError(ContextBuildError):
    """The Brain knowledge base failed canonical validation."""


def _label(item: BrainItem, field: str) -> str:
    return f"{item.source_path}:{item.metadata_line} ({item.id!r}) field {field!r}"


def _strings(item: BrainItem, field: str, *, required: bool = False) -> tuple[str, ...]:
    if field not in item.metadata:
        if required:
            raise ContextBuildError(f"Missing routing field at {_label(item, field)}.")
        return ()
    value = item.metadata[field]
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        raise ContextBuildError(f"Expected a list of strings at {_label(item, field)}.")
    return tuple(value)


def _mapping(item: BrainItem, field: str) -> Mapping[str, Any]:
    value = item.metadata.get(field, {})
    if not isinstance(value, Mapping):
        raise ContextBuildError(f"Expected a mapping at {_label(item, field)}.")
    return value


def _nested_strings(item: BrainItem, field: str, child: str) -> tuple[str, ...]:
    mapping = _mapping(item, field)
    if child not in mapping:
        return ()
    value = mapping[child]
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        raise ContextBuildError(f"Expected a list of strings at {_label(item, field + '.' + child)}.")
    return tuple(value)


def _blocking(item: BrainItem) -> Mapping[str, bool]:
    mapping = _mapping(item, "blocking")
    if any(not isinstance(key, str) or not isinstance(value, bool) for key, value in mapping.items()):
        raise ContextBuildError(f"Expected boolean action flags at {_label(item, 'blocking')}.")
    return mapping


def _applicable(item: BrainItem, intent: str, domains: set[str]) -> tuple[str, ...]:
    intents = _nested_strings(item, "applies_to", "intents")
    item_domains = _nested_strings(item, "applies_to", "domains")
    reasons = []
    if intent in intents:
        reasons.append(f"matched_intent:{intent}")
    reasons.extend(f"matched_domain:{domain}" for domain in sorted(domains & set(item_domains)))
    return tuple(reasons)


def _matched(
    item: BrainItem,
    intent: str,
    domains: set[str],
    tokens: frozenset[str],
) -> tuple[str, ...]:
    reasons = list(_applicable(item, intent, domains))
    reasons.extend(
        f"matched_domain:{domain}"
        for domain in sorted(domains & set(_strings(item, "domains")))
    )
    reasons.extend(
        f"matched_keyword:{word}"
        for word in sorted(tokens & set(_strings(item, "keywords")))
    )
    return tuple(reasons)


def _selected(item: BrainItem, tier: str, reasons: set[str]) -> SelectedContextItem:
    assert isinstance(item.id, str) and isinstance(item.revision, int) and isinstance(item.type, str)
    return SelectedContextItem(item.id, item.revision, item.type, tier, item.content, tuple(sorted(reasons)))


def _execution(resolutions: list[QuestionResolution]) -> ExecutionPolicy:
    missing = [resolution for resolution in resolutions if resolution.status == "missing"]
    safe = ("read_repository", "search_code", "inspect_git_history", "prepare_plan", "ask_questions")
    if any(resolution.severity == "critical" for resolution in missing):
        return ExecutionPolicy("clarification_required", safe, ("modify_code", "commit", "deploy"))
    if any(resolution.severity == "high" for resolution in missing):
        return ExecutionPolicy("investigation_required", safe, ("commit", "deploy"))
    return ExecutionPolicy("ready", safe + ("modify_code", "run_tests", "commit"), ())


def build_context(
    request: RequestPackage,
    brain_path: Path = Path(".brain"),
    max_supporting_items: int = 5,
) -> ContextPackage:
    """Validate a Brain and build a deterministic question-driven package."""
    if max_supporting_items < 0:
        raise ContextBuildError("max_supporting_items must be zero or greater.")
    validation = validate_path(brain_path)
    if not validation.success:
        details = "; ".join(f"{issue.code} {issue.path}:{issue.line} {issue.message}" for issue in validation.issues)
        raise BrainContentError(f"Brain validation failed: {details}")
    items = sorted(validation.items, key=lambda item: str(item.id))
    approved = {item.id: item for item in items if isinstance(item.id, str) and item.status == "approved"}
    classification = classify_task(request)
    domains = set(classification.domains)
    tokens = task_tokens(request.task)

    reasons: dict[str, set[str]] = {}
    playbooks: list[BrainItem] = []
    required_question_ids: set[str] = set()
    required_item_ids: set[str] = set()
    for item in approved.values():
        if item.type == "playbook":
            applicable = _applicable(item, classification.intent, domains)
            if applicable:
                playbooks.append(item)
                reasons.setdefault(str(item.id), set()).update(applicable)
                for question_id in _strings(item, "required_questions"):
                    required_question_ids.add(question_id)
                    reasons.setdefault(question_id, set()).add(f"required_by_playbook:{item.id}")
                for item_id in _strings(item, "required_items"):
                    required_item_ids.add(item_id)
                    reasons.setdefault(item_id, set()).add(f"required_by_playbook:{item.id}")

    questions: list[BrainItem] = []
    for item in approved.values():
        if item.type != "question":
            continue
        applicable = _applicable(item, classification.intent, domains)
        if applicable or item.id in required_question_ids:
            questions.append(item)
            reasons.setdefault(str(item.id), set()).update(applicable)

    resolutions: list[QuestionResolution] = []
    answer_ids: set[str] = set()
    for question in sorted(questions, key=lambda item: str(item.id)):
        configured_mode = question.metadata.get("answer_mode")
        if configured_mode is None:
            answer_mode = "knowledge" if "answer_from" in question.metadata else "request"
        elif isinstance(configured_mode, str) and configured_mode in {"knowledge", "request"}:
            answer_mode = configured_mode
        else:
            raise ContextBuildError(
                f"Expected 'knowledge' or 'request' at {_label(question, 'answer_mode')}."
            )
        configured_references = (
            _strings(question, "answer_from") if "answer_from" in question.metadata else ()
        )
        references = configured_references if answer_mode == "knowledge" else ()
        resolved_ids = tuple(reference for reference in references if reference in approved)
        missing_ids = tuple(reference for reference in references if reference not in approved)
        request_answer = request.answers.get(str(question.id))
        if request_answer is not None and not isinstance(request_answer, str):
            raise ContextBuildError(
                f"Request answer for {question.id!r} must be a string."
            )
        if request_answer is not None:
            request_answer = request_answer.strip() or None
        missing = (
            not references or bool(missing_ids)
            if answer_mode == "knowledge"
            else request_answer is None
        )
        severity = question.metadata.get("severity", "medium")
        if not isinstance(severity, str):
            raise ContextBuildError(f"Expected a string at {_label(question, 'severity')}.")
        _blocking(question)
        resolutions.append(
            QuestionResolution(
                question_id=str(question.id),
                question_text=question.content,
                severity=severity,
                status="missing" if missing else "resolved",
                answer_mode=answer_mode,
                answer_item_ids=resolved_ids,
                missing_answer_item_ids=missing_ids,
                request_answer=request_answer if answer_mode == "request" else None,
            )
        )
        for answer_id in resolved_ids:
            answer_ids.add(answer_id)
            reasons.setdefault(answer_id, set()).add(f"answers_question:{question.id}")

    critical_ids: set[str] = set()
    required_ids = {str(item.id) for item in playbooks} | answer_ids | required_item_ids
    matched_ids: set[str] = set()
    for item_id, item in approved.items():
        if item.type == "question":
            continue
        item_reasons = _matched(item, classification.intent, domains, tokens)
        if item_reasons:
            matched_ids.add(item_id)
            reasons.setdefault(item_id, set()).update(item_reasons)
            if item.type == "contract":
                if item.metadata.get("severity") == "critical":
                    critical_ids.add(item_id)
                else:
                    required_ids.add(item_id)
            elif item.type == "verification":
                required_ids.add(item_id)
    for item_id in tuple(required_ids):
        item = approved.get(item_id)
        if item is not None and item.type == "question":
            required_ids.discard(item_id)
            continue
        if item is not None and item.metadata.get("severity") == "critical":
            critical_ids.add(item_id)
    required_ids -= critical_ids
    eligible = sorted(matched_ids - critical_ids - required_ids)
    supporting_ids = set(eligible[:max_supporting_items])
    available_ids = set(eligible[max_supporting_items:])

    def tier(item_ids: set[str], name: str) -> tuple[SelectedContextItem, ...]:
        return tuple(_selected(approved[item_id], name, reasons.get(item_id, set())) for item_id in sorted(item_ids) if item_id in approved)

    explained_ids = (
        critical_ids
        | required_ids
        | supporting_ids
        | available_ids
        | {str(question.id) for question in questions}
    )
    explanations = {
        item_id: tuple(sorted(values))
        for item_id, values in reasons.items()
        if item_id in explained_ids
    }
    return ContextPackage(
        schema_version="0.1",
        request=request,
        classification=classification,
        execution_policy=_execution(resolutions),
        question_resolutions=tuple(resolutions),
        critical_items=tier(critical_ids, "critical"),
        required_items=tier(required_ids, "required"),
        supporting_items=tier(supporting_ids, "supporting"),
        available_on_demand_items=tier(available_ids, "available_on_demand"),
        selection_explanations=explanations,
    )
