"""Project Brain Engine public API."""

from brain_engine.domain import BrainItem, ValidationIssue, ValidationResult
from brain_engine.context import BrainContentError, ContextBuildError, build_context, classify_task
from brain_engine.domain import ContextPackage, RequestPackage, TaskClassification
from brain_engine.validation import ValidationOperationalError, validate_path

__version__ = "0.1.0"

__all__ = [
    "BrainContentError", "BrainItem", "ContextBuildError", "ContextPackage", "RequestPackage",
    "TaskClassification", "ValidationIssue", "ValidationOperationalError", "ValidationResult",
    "__version__", "build_context", "classify_task", "validate_path",
]
