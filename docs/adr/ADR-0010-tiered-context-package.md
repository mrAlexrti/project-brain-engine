# ADR-0010: Tiered Context Package

- **Status:** Accepted
- **Date:** 2026-07-12

## Decision

Context is divided into four tiers:

1. **Critical** — blocking questions, critical contracts, conflicts, forbidden actions.
2. **Required** — primary knowledge, playbook, affected areas, verification.
3. **Supporting** — related decisions, history, examples, non-critical risks.
4. **Available on demand** — discoverable by ID without immediate inclusion.

## Principle

> Critical knowledge is guaranteed. Supporting knowledge is budgeted. Additional knowledge is retrievable on demand.

Token budgets may reduce Supporting context but must not remove Critical context.
