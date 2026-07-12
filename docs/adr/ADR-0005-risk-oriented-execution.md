# ADR-0005: Risk-Oriented Execution Model

- **Status:** Accepted
- **Date:** 2026-07-12

## Decision

The engine uses four execution states:

- `ready`;
- `investigation_required`;
- `clarification_required`;
- `blocked`.

Each result includes explicit allowed and forbidden actions.

Missing critical information may block code changes while still allowing repository investigation and planning.

## Rationale

A binary allow/deny model is too rigid. Safe investigation should remain possible even when implementation is not yet justified.
