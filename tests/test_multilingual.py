import json
from pathlib import Path

import pytest
import yaml

from brain_engine.context import build_context, classify_task
from brain_engine.domain import RequestPackage

from test_context import block, brain


@pytest.mark.parametrize(
    ("task", "intent"),
    [
        ("Исправить ошибку checkout", "bugfix"),
        ("Виправити помилку checkout", "bugfix"),
        ("Добавить функцию экспорта", "feature"),
        ("Додати функцію експорту", "feature"),
        ("Изменить архитектуру schema", "architecture_change"),
        ("Змінити архітектуру schema", "architecture_change"),
        ("Проверить модуль parser", "review"),
        ("Перевірити модуль parser", "review"),
    ],
)
def test_multilingual_intents(task: str, intent: str) -> None:
    assert classify_task(RequestPackage(task)).intent == intent


def test_unicode_retrieval_and_original_serialization(tmp_path: Path) -> None:
    original = "Исправить помилку в модуле ОплатаService без перевода"
    path = brain(
        tmp_path,
        block(
            "knowledge.payment",
            "knowledge",
            keywords=["оплатаservice", "помилка"],
            content="Модуль ОплатаService обрабатывает оплату.",
        ),
    )
    package = build_context(RequestPackage(original), path)
    assert package.request.task == original
    assert "knowledge.payment" in {item.item_id for item in package.supporting_items}
    assert json.loads(json.dumps(package.to_dict(), ensure_ascii=False))["request"]["task"] == original
    assert yaml.safe_load(yaml.safe_dump(package.to_dict(), allow_unicode=True))["request"]["task"] == original
