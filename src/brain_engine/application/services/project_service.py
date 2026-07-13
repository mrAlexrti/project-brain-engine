"""Local project profiles and stable repository inspection."""

from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any

from brain_engine.experiment.metadata import inspect_repository
from brain_engine.persistence import read_yaml, write_yaml


class ProjectService:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.profiles = self.data_dir / "projects.yaml"

    def list_profiles(self) -> list[dict[str, Any]]:
        if not self.profiles.exists():
            return []
        return list(read_yaml(self.profiles).get("projects", []))

    def connect(self, path: Path) -> dict[str, Any]:
        metadata = inspect_repository(path)
        project_id = hashlib.sha256(metadata["repository_path"].encode("utf-8")).hexdigest()[:16]
        profile = {**metadata, "project_id": project_id, "opened_at": datetime.now().astimezone().isoformat()}
        existing = [item for item in self.list_profiles() if item["repository_path"] != profile["repository_path"]]
        write_yaml(self.profiles, {"projects": [profile, *existing][:20]})
        return profile

    def get(self, project_id: str) -> dict[str, Any]:
        matches = [item for item in self.list_profiles() if item.get("project_id") == project_id]
        if len(matches) != 1:
            raise ValueError("Project not found.")
        return matches[0]
