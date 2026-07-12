# ADR-0001: Hybrid Knowledge Model

- **Status:** Accepted
- **Date:** 2026-07-12

## Context

Documents are easy for people to read, but too coarse for precise retrieval and per-item trust metadata. Standalone machine records are precise, but hundreds of YAML files would be unpleasant to maintain.

## Decision

A **Brain Item** is the logical unit of knowledge.

A **Document** is a human-readable container and presentation layer for one or more Brain Items.

The engine retrieves and reasons over Brain Items, while humans primarily author and review Markdown documents.

## Consequences

Positive:

- human-readable project memory;
- atomic retrieval;
- per-item trust metadata;
- future migration to SQLite or graph storage without changing the domain model.

Negative:

- a structured embedding format is required;
- validators must protect Item boundaries and IDs;
- authoring tools may eventually be useful.
