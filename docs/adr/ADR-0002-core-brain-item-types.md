# ADR-0002: Core Brain Item Types

- **Status:** Accepted
- **Date:** 2026-07-12

## Decision

Project Brain Engine defines six core Brain Item types:

- `knowledge`;
- `question`;
- `contract`;
- `decision`;
- `playbook`;
- `verification`.

Concepts such as fact, assumption, risk, and recommendation are represented through metadata rather than additional core types.

## Rationale

A small strict type system gives the engine reliable semantics without creating an unmanageable taxonomy.
