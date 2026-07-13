from pathlib import Path


def test_privacy_and_multilingual_docs_are_separate_and_focused() -> None:
    privacy = Path("docs/PRIVACY.md")
    multilingual = Path("docs/MULTILINGUAL_SUPPORT.md")
    assert privacy.is_file() and multilingual.is_file()
    privacy_text = privacy.read_text(encoding="utf-8")
    multilingual_text = multilingual.read_text(encoding="utf-8")
    assert "# Privacy" in privacy_text and "telemetry" in privacy_text
    assert "# Multilingual" in multilingual_text and "Unicode" in multilingual_text
    assert "Unicode NFKC" not in privacy_text
    assert "telemetry, analytics" not in multilingual_text
