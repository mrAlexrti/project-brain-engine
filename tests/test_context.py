import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from brain_engine.cli import app
from brain_engine.context import ContextBuildError, build_context, classify_task
from brain_engine.domain import RequestPackage
from brain_engine.validation import validate_path

ROOT = Path(__file__).parents[1]
REQUIRED_IDS = {
    "project.purpose", "project.mission", "project.model-independence",
    "architecture.hybrid-knowledge-model", "architecture.input-agnostic-engine",
    "architecture.stable-item-identity", "architecture.hybrid-context-retrieval",
    "architecture.tiered-context-package", "architecture.proposal-first-learning",
    "contract.no-silent-conflict-resolution", "contract.critical-knowledge-human-approval",
    "contract.deterministic-core", "contract.critical-context-is-never-truncated",
    "question.change.project-goal", "question.change.affected-contracts",
    "question.change.verification", "question.architecture.existing-decisions",
    "playbook.architecture-change", "playbook.python-change",
    "verification.python-quality", "verification.brain-validation",
}


def block(item_id: str, item_type: str, *, status: str = "approved", content: str = "Content.", **metadata: object) -> str:
    values = {"id": item_id, "type": item_type, "revision": 1, "status": status, **metadata}
    serialized = yaml.safe_dump(values, sort_keys=False).rstrip()
    return f"<!-- brain:item:start -->\n```yaml\n{serialized}\n```\n\n{content}\n<!-- brain:item:end -->\n"


def brain(tmp_path: Path, *items: str) -> Path:
    path = tmp_path / ".brain"
    path.mkdir(parents=True)
    (path / "items.md").write_text("\n".join(items), encoding="utf-8")
    return path


def test_repository_brain_is_valid_and_complete() -> None:
    result = validate_path(ROOT / ".brain")
    assert result.success
    assert len(result.items) == 21
    assert REQUIRED_IDS <= {item.id for item in result.items}


@pytest.mark.parametrize(
    ("task", "intent", "risk"),
    [
        ("Change the core architecture", "architecture_change", "high"),
        ("Fix the broken parser", "bugfix", "medium"),
        ("Reproduce and fix the checkout defect", "bugfix", "medium"),
        ("Fix the defect while preserving the existing architecture and design", "bugfix", "medium"),
        ("Implement a CLI command", "feature", "medium"),
        ("Review the parser", "review", "low"),
    ],
)
def test_intent_classification(task: str, intent: str, risk: str) -> None:
    result = classify_task(RequestPackage(task))
    assert (result.intent, result.risk) == (intent, risk)


def test_multiple_domains_and_deterministic_precedence() -> None:
    result = classify_task(RequestPackage("Review and implement architecture parser tests in Python CLI"))
    assert result.intent == "architecture_change"
    assert result.domains == ("architecture", "cli", "python", "testing", "validation")


def test_architecture_change_without_defect_signal_remains_architecture_change() -> None:
    result = classify_task(RequestPackage("Change the architecture contract and schema"))
    assert (result.intent, result.risk) == ("architecture_change", "high")


@pytest.mark.parametrize(
    ("answer_status", "include_answer", "expected"),
    [
        ("approved", True, "resolved"),
        ("approved", False, "missing"),
        ("proposed", True, "missing"),
        ("deprecated", True, "missing"),
    ],
)
def test_question_resolution(
    tmp_path: Path, answer_status: str, include_answer: bool, expected: str
) -> None:
    question = block(
        "question.test", "question", severity="high",
        applies_to={"intents": ["feature"]}, answer_from=["knowledge.answer"],
    )
    items = [question]
    if include_answer:
        items.append(block("knowledge.answer", "knowledge", status=answer_status))
    package = build_context(RequestPackage("Implement support"), brain(tmp_path, *items))
    assert package.question_resolutions[0].status == expected
    assert package.question_resolutions[0].missing_answer_item_ids == (() if expected == "resolved" else ("knowledge.answer",))


def test_question_without_answer_from_is_missing(tmp_path: Path) -> None:
    path = brain(tmp_path, block("question.test", "question", severity="high", applies_to={"intents": ["review"]}))
    package = build_context(RequestPackage("Review this"), path)
    assert package.question_resolutions[0].status == "missing"
    assert package.question_resolutions[0].missing_answer_item_ids == ()
    assert package.question_resolutions[0].answer_mode == "request"


def test_request_mode_requires_explicit_request_answer(tmp_path: Path) -> None:
    path = brain(
        tmp_path,
        block(
            "question.request",
            "question",
            severity="critical",
            applies_to={"intents": ["review"]},
            answer_mode="request",
            answer_from=["project.purpose"],
        ),
        block("project.purpose", "knowledge"),
    )
    missing = build_context(RequestPackage("Review this"), path)
    assert missing.question_resolutions[0].status == "missing"
    resolved = build_context(
        RequestPackage(
            "Review this",
            answers={"question.request": "Achieve this task-specific outcome."},
        ),
        path,
    )
    resolution = resolved.question_resolutions[0]
    assert resolution.status == "resolved"
    assert resolution.request_answer == "Achieve this task-specific outcome."
    assert resolution.to_dict()["request_answer"] == "Achieve this task-specific outcome."


def test_explicit_and_backward_compatible_knowledge_modes(tmp_path: Path) -> None:
    path = brain(
        tmp_path,
        block(
            "question.explicit",
            "question",
            applies_to={"intents": ["review"]},
            answer_mode="knowledge",
            answer_from=["knowledge.answer"],
        ),
        block(
            "question.compatible",
            "question",
            applies_to={"intents": ["review"]},
            answer_from=["knowledge.answer"],
        ),
        block("knowledge.answer", "knowledge"),
    )
    package = build_context(RequestPackage("Review this"), path)
    assert [(item.answer_mode, item.status) for item in package.question_resolutions] == [
        ("knowledge", "resolved"),
        ("knowledge", "resolved"),
    ]


def selection_brain(tmp_path: Path) -> Path:
    return brain(
        tmp_path,
        block("question.required", "question", severity="medium", answer_from=["knowledge.answer"]),
        block("knowledge.answer", "knowledge"),
        block("contract.required", "contract", severity="high"),
        block(
            "playbook.python", "playbook", applies_to={"intents": ["feature"]},
            required_questions=["question.required"], required_items=["contract.required"],
        ),
        block("knowledge.a", "knowledge", domains=["validation"]),
        block("knowledge.b", "knowledge", domains=["validation"]),
        block("knowledge.c", "knowledge", domains=["validation"]),
    )


def test_playbook_references_reasons_tiers_and_budget(tmp_path: Path) -> None:
    package = build_context(RequestPackage("Implement parser validation"), selection_brain(tmp_path), 1)
    required = {item.item_id: item for item in package.required_items}
    assert "playbook.python" in required
    assert package.question_resolutions[0].question_id == "question.required"
    assert package.selection_explanations["question.required"] == (
        "required_by_playbook:playbook.python",
    )
    assert "contract.required" in required
    assert "required_by_playbook:playbook.python" in required["contract.required"].selection_reasons
    all_ids = [item.item_id for tier in (package.critical_items, package.required_items, package.supporting_items, package.available_on_demand_items) for item in tier]
    assert len(all_ids) == len(set(all_ids))
    assert not any(item_id.startswith("question.") for item_id in all_ids)
    assert [item.item_id for item in package.supporting_items] == ["knowledge.a"]
    assert [item.item_id for item in package.available_on_demand_items] == ["knowledge.b", "knowledge.c"]
    for tier in (
        package.critical_items,
        package.required_items,
        package.supporting_items,
        package.available_on_demand_items,
    ):
        assert [item.item_id for item in tier] == sorted(item.item_id for item in tier)
    assert package.to_dict() == build_context(RequestPackage("Implement parser validation"), selection_brain_existing(tmp_path), 1).to_dict()


def selection_brain_existing(tmp_path: Path) -> Path:
    return tmp_path / ".brain"


@pytest.mark.parametrize(
    ("severity", "with_answer", "status"),
    [("critical", False, "clarification_required"), ("high", False, "investigation_required"), ("critical", True, "ready")],
)
def test_execution_policy(tmp_path: Path, severity: str, with_answer: bool, status: str) -> None:
    items = [block("question.test", "question", severity=severity, applies_to={"intents": ["review"]}, answer_from=["knowledge.answer"])]
    if with_answer:
        items.append(block("knowledge.answer", "knowledge"))
    package = build_context(RequestPackage("Review this"), brain(tmp_path, *items))
    assert package.execution_policy.status == status


def test_explicit_action_prohibitions_override_ready_permissions(tmp_path: Path) -> None:
    package = build_context(
        RequestPackage("Fix the widget defect. Do not commit or push changes."),
        brain(tmp_path),
    )
    assert package.execution_policy.status == "ready"
    assert "commit" not in package.execution_policy.allowed_actions
    assert "push" not in package.execution_policy.allowed_actions
    assert {"commit", "push"} <= set(package.execution_policy.forbidden_actions)


def test_quoted_or_described_prohibition_is_not_treated_as_an_instruction(tmp_path: Path) -> None:
    package = build_context(
        RequestPackage('Review documentation that says "do not commit" to explain the policy.'),
        brain(tmp_path),
    )
    assert "commit" in package.execution_policy.allowed_actions


def test_project_owned_vocabulary_retrieval_is_relevant_bounded_and_stable(
    tmp_path: Path,
) -> None:
    path = brain(
        tmp_path,
        block(
            "contract.nebula-labels", "contract", severity="high",
            tags=["nebula", "labels"], content="Nebula labels must follow the active dialect.",
        ),
        block(
            "playbook.nebula-change", "playbook", tags=["nebula", "change"],
            required_questions=["question.nebula-owner"],
            content="Safely change nebula rendering and preserve existing behavior.",
        ),
        block(
            "verification.nebula-rendering", "verification", tags=["nebula", "verification"],
            content="Verify nebula rendering in each supported dialect.",
        ),
        block(
            "knowledge.nebula-mechanism", "knowledge", tags=["nebula", "rendering"],
            content="The nebula renderer owns dialect-aware labels.",
        ),
        block(
            "question.nebula-owner", "question", severity="medium", tags=["nebula"],
            answer_from=["knowledge.nebula-mechanism"], content="Which component owns nebula labels?",
        ),
        block(
            "knowledge.unrelated-payments", "knowledge", tags=["payments"],
            content="Payment settlement uses an unrelated external ledger.",
        ),
    )
    request = RequestPackage(
        "Reproduce and fix the nebula label defect. Preserve its rendering mechanism and run verification."
    )
    first = build_context(request, path, max_supporting_items=2)
    second = build_context(request, path, max_supporting_items=2)
    assert first.to_dict() == second.to_dict()
    tiered = {
        item.item_id
        for tier in (
            first.critical_items,
            first.required_items,
            first.supporting_items,
            first.available_on_demand_items,
        )
        for item in tier
    }
    assert {
        "contract.nebula-labels",
        "playbook.nebula-change",
        "verification.nebula-rendering",
        "knowledge.nebula-mechanism",
    } <= tiered
    assert "knowledge.unrelated-payments" not in tiered
    assert "question.nebula-owner" not in tiered
    assert [item.question_id for item in first.question_resolutions] == ["question.nebula-owner"]
    assert len(first.supporting_items) <= 2
    for tier in (
        first.critical_items,
        first.required_items,
        first.supporting_items,
        first.available_on_demand_items,
    ):
        assert [item.item_id for item in tier] == sorted(item.item_id for item in tier)


def test_invalid_routing_metadata_fails_cleanly(tmp_path: Path) -> None:
    path = brain(tmp_path, block("knowledge.test", "knowledge", domains="invalid"))
    with pytest.raises(ContextBuildError, match="list of strings"):
        build_context(RequestPackage("Review knowledge"), path)


def test_cli_console_json_and_yaml() -> None:
    runner = CliRunner()
    args = ["context", "Add pytest validation", "--brain-path", str(ROOT / ".brain")]
    console_result = runner.invoke(app, args)
    json_result = runner.invoke(app, args + ["--format", "json"])
    yaml_result = runner.invoke(app, args + ["--format", "yaml"])
    assert console_result.exit_code == 0
    assert "Execution status" in console_result.stdout
    assert json.loads(json_result.stdout)["request"]["task"] == "Add pytest validation"
    assert yaml.safe_load(yaml_result.stdout)["schema_version"] == "0.1"


def test_cli_context_failures_and_clarification_success(tmp_path: Path) -> None:
    runner = CliRunner()
    missing = runner.invoke(app, ["context", "Review", "-b", str(tmp_path / "missing")])
    invalid_path = brain(tmp_path, "<!-- brain:item:start -->\ninvalid\n<!-- brain:item:end -->")
    invalid = runner.invoke(app, ["context", "Review", "-b", str(invalid_path)])
    invalid_format = runner.invoke(app, ["context", "Review", "-f", "xml"])
    negative = runner.invoke(app, ["context", "Review", "--max-supporting", "-1"])
    assert missing.exit_code == 2 and "Operational error" in missing.stdout
    assert invalid.exit_code == 1 and "Invalid Brain" in invalid.stdout
    assert invalid_format.exit_code == 2 and "Invalid format" in invalid_format.stdout
    assert negative.exit_code == 2 and "zero or greater" in negative.stdout

    other = tmp_path / "other"
    clarification_path = brain(other, block("question.critical", "question", severity="critical", applies_to={"intents": ["review"]}))
    clarification = runner.invoke(app, ["context", "Review", "-b", str(clarification_path)])
    assert clarification.exit_code == 0
    assert "clarification_required" in clarification.stdout


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("malformed", "QUESTION_ID=ANSWER"),
        ("=answer", "Question ID must not be empty"),
        ("question.test=   ", "must not be empty"),
    ],
)
def test_cli_rejects_malformed_answers(value: str, message: str) -> None:
    result = CliRunner().invoke(app, ["context", "Review", "--answer", value])
    assert result.exit_code == 2
    assert message in result.stdout


def test_cli_rejects_duplicate_answer_ids() -> None:
    result = CliRunner().invoke(
        app,
        [
            "context", "Review",
            "--answer", "question.test=first",
            "--answer", "question.test=second",
        ],
    )
    assert result.exit_code == 2
    assert "Duplicate Question ID" in result.stdout


def test_cli_accepts_multiple_answers_and_splits_first_equals() -> None:
    result = CliRunner().invoke(
        app,
        [
            "context", "Change the core architecture model", "--format", "json",
            "--brain-path", str(ROOT / ".brain"),
            "--answer", "question.change.project-goal=Support key=value metadata",
            "--answer", "question.change.affected-contracts=Preserve deterministic contracts",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["request"]["answers"]["question.change.project-goal"] == "Support key=value metadata"
    assert payload["execution_policy"]["status"] == "ready"


def test_architecture_request_answers_control_execution_and_questions_are_not_tiered() -> None:
    task = "Change the core architecture model"
    missing = build_context(RequestPackage(task), ROOT / ".brain")
    resolutions = {item.question_id: item for item in missing.question_resolutions}
    assert resolutions["question.change.project-goal"].status == "missing"
    assert resolutions["question.change.affected-contracts"].status == "missing"
    assert missing.execution_policy.status == "clarification_required"
    assert {"modify_code", "commit", "deploy"} <= set(missing.execution_policy.forbidden_actions)

    answered = build_context(
        RequestPackage(
            task,
            answers={
                "question.change.project-goal": "Support richer normalized engineering requests",
                "question.change.affected-contracts": "Preserve input-agnostic and deterministic core contracts",
            },
        ),
        ROOT / ".brain",
    )
    assert answered.execution_policy.status == "ready"
    tiered_ids = {
        item.item_id
        for tier in (
            answered.critical_items,
            answered.required_items,
            answered.supporting_items,
            answered.available_on_demand_items,
        )
        for item in tier
    }
    assert not tiered_ids & {item.question_id for item in answered.question_resolutions}
