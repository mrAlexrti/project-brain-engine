# Multilingual Support

Task text and Brain Item content are authoritative in their exact original form. JSON and YAML retain Unicode text. The engine does not translate or rewrite it.

For matching only, text is normalized with Unicode NFKC, casefolded, and tokenized into Unicode letter/digit terms including mixed Cyrillic and Latin technical identifiers. Explicit deterministic intent dictionaries cover English, Russian, and Ukrainian bugfix, feature, architecture-change, and review signals.

Retrieval compares task terms with Item ID, title, tags, domains, keywords, sources, and content. Translation is not part of the trust model.
