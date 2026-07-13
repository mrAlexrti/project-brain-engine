"""Safe one-Item-per-file editing over the canonical validator."""

from pathlib import Path
from typing import Any

from brain_engine.initialization.templates import item_markdown
from brain_engine.persistence import atomic_write_text
from brain_engine.validation import validate_path
from brain_engine.validation.validator import ID_PATTERN


class BrainService:
    TYPE_DIRECTORIES = {
        "knowledge": "knowledge", "decision": "decisions", "contract": "contracts",
        "question": "questions", "playbook": "playbooks", "verification": "verification",
    }

    def list_items(self, brain: Path) -> list[Any]:
        return validate_path(brain).items

    def save_item(self, brain: Path, metadata: dict[str, Any], content: str) -> Path:
        item_id = str(metadata.get("id", ""))
        if ID_PATTERN.fullmatch(item_id) is None:
            raise ValueError("Invalid Item ID.")
        item_type = str(metadata.get("type", ""))
        if item_type not in self.TYPE_DIRECTORIES:
            raise ValueError("Invalid Item type.")
        metadata = {**metadata, "status": "proposed"}
        target = (brain.resolve() / "items" / self.TYPE_DIRECTORIES[item_type] / f"{item_id}.md").resolve()
        target.relative_to(brain.resolve())
        if target.exists():
            raise ValueError("Refusing to overwrite an existing Item.")
        atomic_write_text(target, item_markdown(metadata, content))
        return target

    def change_status(self, brain: Path, item_id: str, status: str, confirmed: bool) -> None:
        if status == "approved" and not confirmed:
            raise ValueError("Approval requires explicit owner confirmation.")
        if status not in {"approved", "deprecated"}:
            raise ValueError("Invalid status transition.")
        result = validate_path(brain)
        matches = [item for item in result.items if item.id == item_id]
        if len(matches) != 1:
            raise ValueError("Item not found or ambiguous.")
        item = matches[0]
        text = item.source_path.read_text(encoding="utf-8")
        old = f"status: {item.status}"
        if text.count(old) != 1:
            raise ValueError("Cannot safely update Item status.")
        atomic_write_text(item.source_path, text.replace(old, f"status: {status}", 1))

    def update_item(self, brain: Path, item_id: str, metadata: dict[str, Any], content: str) -> Path:
        result = validate_path(brain)
        matches = [item for item in result.items if item.id == item_id]
        if len(matches) != 1:
            raise ValueError("Item not found or ambiguous.")
        item = matches[0]
        item_type = str(metadata.get("type", item.type))
        if item_type != item.type or item_type not in self.TYPE_DIRECTORIES:
            raise ValueError("An Item type cannot change during editing.")
        values = {**item.metadata, **metadata, "id": item_id, "type": item_type}
        revision = item.revision if isinstance(item.revision, int) else 0
        values.update({"revision": revision + 1, "status": "proposed"})
        atomic_write_text(item.source_path, item_markdown(values, content))
        return item.source_path
