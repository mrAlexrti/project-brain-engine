# ADR-0007: Stable Identities and Immutable Revisions

- **Status:** Accepted
- **Date:** 2026-07-12

## Decision

Each Brain Item has a stable logical ID.

Content changes create a new immutable revision rather than a new ID.

Approval determines the active revision for a specific project state.

## Principle

> Identity is stable. Revisions are immutable. Approval selects the active truth.

## MVP Implementation

Git stores history. The current Markdown representation stores the active revision and revision metadata.
