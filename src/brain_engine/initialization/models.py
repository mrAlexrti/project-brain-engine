from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class InitializationRequest:
    path: Path
    project_name: str
    project_purpose: str
    primary_technology: str
    language: str = "en"


@dataclass(frozen=True, slots=True)
class InitializationResult:
    brain_path: Path
    created_files: tuple[Path, ...]
    proposed_item_count: int
    validation_errors: int
