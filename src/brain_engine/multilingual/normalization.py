"""Unicode-safe normalization used only for matching."""

import re
import unicodedata

TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[_-][^\W_]+)*", re.UNICODE)


def normalized_text(text: str) -> str:
    """Return deterministic NFKC/casefold text without changing stored input."""
    return unicodedata.normalize("NFKC", text).casefold()


def word_tokens(text: str) -> frozenset[str]:
    """Tokenize Latin, Cyrillic, digits, and mixed technical identifiers."""
    return frozenset(TOKEN_PATTERN.findall(normalized_text(text)))
