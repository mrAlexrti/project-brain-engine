"""Canonical application-created Brain Markdown."""

from typing import Any

import yaml


def item_markdown(metadata: dict[str, Any], content: str) -> str:
    values = {"revision": 1, "status": "proposed", **metadata}
    header = yaml.safe_dump(values, sort_keys=False, allow_unicode=True).rstrip()
    return (
        "<!-- brain:item:start -->\n```yaml\n"
        f"{header}\n```\n\n{content.rstrip()}\n<!-- brain:item:end -->\n"
    )
