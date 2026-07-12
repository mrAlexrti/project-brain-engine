"""Explicit keyword-based task classification."""

import re

from brain_engine.domain.context import RequestPackage, TaskClassification

# Precedence is architectural change, bug fix, feature, review, then general.
INTENT_KEYWORDS: tuple[tuple[str, frozenset[str]], ...] = (
    ("architecture_change", frozenset({"architecture", "architectural", "adr", "rfc", "design", "model", "schema", "contract", "decision"})),
    ("bugfix", frozenset({"fix", "bug", "error", "failure", "broken", "incorrect"})),
    ("feature", frozenset({"add", "create", "implement", "introduce", "support"})),
    ("review", frozenset({"review", "inspect", "analyze", "check", "assess"})),
)

DOMAIN_KEYWORDS: dict[str, frozenset[str]] = {
    "architecture": frozenset({"architecture", "architectural", "adr", "rfc", "design", "model", "schema", "contract", "decision"}),
    "context": frozenset({"context", "retrieval", "routing", "question", "package"}),
    "validation": frozenset({"validate", "validation", "validator", "parser", "parse"}),
    "cli": frozenset({"cli", "command", "typer", "console"}),
    "knowledge": frozenset({"knowledge", "brain", "item", "memory"}),
    "testing": frozenset({"test", "tests", "testing", "pytest", "ruff", "quality"}),
    "documentation": frozenset({"documentation", "document", "docs", "markdown", "readme"}),
    "python": frozenset({"python", "pytest", "ruff", "pyyaml", "typer"}),
}


def task_tokens(text: str) -> frozenset[str]:
    """Normalize task text into deterministic lowercase word tokens."""
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def classify_task(request: RequestPackage) -> TaskClassification:
    """Classify a request using explicit intent precedence and domain maps."""
    tokens = task_tokens(request.task)
    intent = "general"
    for candidate, keywords in INTENT_KEYWORDS:
        if tokens & keywords:
            intent = candidate
            break
    domains = tuple(sorted(domain for domain, words in DOMAIN_KEYWORDS.items() if tokens & words))
    risk = "high" if intent == "architecture_change" else "medium" if intent in {"bugfix", "feature"} else "low"
    return TaskClassification(intent=intent, domains=domains, risk=risk)
