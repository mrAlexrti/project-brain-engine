# ADR-0009: Hybrid Explainable Context Retrieval

- **Status:** Accepted
- **Date:** 2026-07-12

## Decision

Context retrieval begins with deterministic signals:

- intent;
- domain;
- IDs;
- tags;
- keywords;
- paths;
- explicit relations;
- mandatory contracts, questions, playbooks, and verification Items.

Optional semantic retrieval may expand recall.

Every selected Item must include selection reasons.

## Principle

> Deterministic retrieval establishes trust. Semantic retrieval improves recall.

## Constraint

Semantic similarity cannot override approval status, contracts, conflicts, or authority domains.
