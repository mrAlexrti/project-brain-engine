# ADR-0008: Canonical Markdown with Structured Brain Item Blocks

- **Status:** Accepted
- **Date:** 2026-07-12

## Decision

Markdown documents are the canonical authoring representation.

Each Brain Item is enclosed in explicit start and end markers and begins with structured YAML metadata.

```text
<!-- brain:item:start -->
YAML metadata
Human-readable content
<!-- brain:item:end -->
```

A generated machine index is derived, reproducible, disposable, and never edited manually.

## Consequences

The engine requires deterministic parsing and precise validation errors.
