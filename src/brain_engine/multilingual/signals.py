"""Explicit English, Russian, and Ukrainian task intent signals."""

INTENT_SIGNALS: tuple[tuple[str, frozenset[str]], ...] = (
    (
        "bugfix",
        frozenset(
            {
                "fix", "bug", "defect", "error", "failure", "broken", "incorrect",
                "исправить", "ошибка", "дефект", "сломано", "некорректно", "исправление",
                "виправити", "помилка", "дефект", "зламано", "некоректно", "виправлення",
            }
        ),
    ),
    (
        "architecture_change",
        frozenset(
            {
                "architecture", "architectural", "adr", "rfc", "design", "model", "schema",
                "contract", "decision", "архитектура", "архитектурный", "архитектурное",
                "архитектуру", "архитектуры", "схема", "контракт", "решение",
                "архітектура", "архітектурний", "архітектурне", "архітектуру",
                "архітектури", "схема", "контракт", "рішення",
            }
        ),
    ),
    (
        "feature",
        frozenset(
            {
                "add", "create", "implement", "introduce", "support", "feature",
                "добавить", "создать", "реализовать", "внедрить", "поддержать", "функция",
                "додати", "створити", "реалізувати", "впровадити", "підтримати", "функція",
            }
        ),
    ),
    (
        "review",
        frozenset(
            {
                "review", "inspect", "analyze", "check", "assess", "audit",
                "проверить", "обзор", "проанализировать", "оценить", "аудит",
                "перевірити", "огляд", "проаналізувати", "оцінити", "аудит",
            }
        ),
    ),
)
