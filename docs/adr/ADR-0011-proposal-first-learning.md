# ADR-0011: Proposal-First Learning

- **Status:** Accepted
- **Date:** 2026-07-12

## Decision

AI agents may propose new knowledge or revisions.

They do not automatically approve critical project memory.

Approval policies depend on knowledge category.

```yaml
approval_policy:
  business_rule: human_required
  contract: human_required
  architecture_decision: human_required
  code_location: automatic_with_evidence
  dependency_inventory: automatic_allowed
```

## Principle

> AI may propose knowledge. Authority decides what becomes project memory.

## Consequences

Knowledge Proposals require evidence, provenance, confidence, and conflict checks.
