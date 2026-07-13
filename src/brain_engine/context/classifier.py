"""Explicit keyword-based task classification."""

from brain_engine.domain.context import RequestPackage, TaskClassification
from brain_engine.multilingual.normalization import word_tokens
from brain_engine.multilingual.signals import INTENT_SIGNALS

# Explicit defect repair takes precedence over incidental architecture/design words.
# Architecture changes otherwise precede features and reviews.
INTENT_KEYWORDS = INTENT_SIGNALS

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
    """Normalize task text into deterministic Unicode word tokens."""
    return word_tokens(text)


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
