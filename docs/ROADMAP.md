# Project Brain Engine Roadmap

**Status:** Draft  
**Last updated:** 2026-07-13

## Phase 0 — Architecture and Research

Deliverables:

- Manifesto;
- Architecture;
- accepted ADRs;
- open RFCs;
- first experimental methodology.

## Phase 1 — Vertical-Slice MVP

Commands:

```bash
brain init
brain context "<task>"
brain validate
```

Capabilities:

- parse structured Brain Item blocks from Markdown;
- validate IDs, types, revisions, and statuses;
- select Question Sets;
- classify a limited set of intents;
- retrieve Items using deterministic rules;
- produce a tiered Context Package;
- show missing answers and execution restrictions.

Reference scenario:

- `3dkidShop`;
- localization defect;
- controlled A/B experiment.

## Phase 2 — Repository Intelligence

```bash
brain scan
brain index
brain doctor
```

The scanner may produce evidence-backed `proposed` knowledge, but never silently approve business rules.

## Phase 3 — Contract-Aware Review

```bash
brain review
brain diff
```

The engine inspects Git changes, detects contract violations, and proposes knowledge updates.

## Phase 4 — MCP and Agent Integration

Planned tools:

```text
brain.get_context
brain.get_item
brain.get_questions
brain.get_contracts
brain.get_execution_policy
brain.propose_knowledge
brain.review_changes
```

## Phase 5 — Knowledge Graph and Advanced Retrieval

- graph relation expansion;
- optional embeddings;
- impact analysis;
- context budgeting by model;
- historical context reconstruction.

## Phase 6 — Ecosystem

- published specification;
- project templates;
- framework adapters;
- IDE extensions;
- CI integrations;
- enterprise approval policies;
- open-source community.

## Product Rule

Each phase must validate a real hypothesis before the next phase adds complexity.

## Application-first vertical slice

The Phase 1 implementation now includes a local server-rendered application (`brain app` and
`brain-app`), stable repository inspection, proposed-only Brain initialization, deterministic
Unicode matching, and controlled experiment worktree/evidence/evaluation/integrity services.

Direct agent execution, automatic verification, native installers, hosted operation, semantic source
scanning, embeddings, and automatic publication remain deliberately deferred.
