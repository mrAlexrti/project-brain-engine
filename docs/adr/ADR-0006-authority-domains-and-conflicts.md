# ADR-0006: Authority Domains and Explicit Conflicts

- **Status:** Accepted
- **Date:** 2026-07-12

## Decision

Project Brain does not use one global source-priority list.

Authority depends on the knowledge domain:

- business rules → approved contracts and decisions;
- current implementation → source code and configuration;
- current intent → Work/Task Package;
- historical rationale → ADRs and decision Items;
- generated facts → scanner output with evidence and proposed status.

Conflicts between authoritative sources are surfaced explicitly and never resolved silently.

## Consequences

The engine must distinguish declared behaviour, implemented behaviour, and intended change.
