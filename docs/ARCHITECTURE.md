# Project Brain Engine Architecture

**Status:** Draft architecture based on accepted ADRs  
**Last updated:** 2026-07-12

## 1. Purpose

Project Brain Engine is a model-independent knowledge runtime for AI-assisted software development.

It receives a normalized package describing a unit of work and returns a structured Context Package containing the minimum sufficient trusted knowledge required to execute that work safely.

The engine is not coupled to GitHub, Jira, VS Code, MCP, Codex, Claude, Gemini, or any other external system.

## 2. System Context

```text
GitHub Issue ─┐
Jira Ticket ──┤
CLI Command ──┤
MCP Request ──┼──> Input Adapter ──> Work/Task Package
IDE Action ───┤                           │
Human Input ──┘                           ▼
                                  Project Brain Engine
                                           │
                                           ▼
                                     Context Package
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
                  Codex                  Claude                 Gemini
```

## 3. Architectural Goal

The engine must answer five questions before implementation begins:

1. What kind of work is being requested?
2. What project knowledge is relevant?
3. What critical information is missing or conflicting?
4. What actions are allowed or forbidden?
5. How will the result be verified?

## 4. Core Domain Model

### 4.1 Brain Item

A Brain Item is the logical unit of project knowledge.

A Brain Item has:

- a stable logical ID;
- one of six core types;
- an immutable revision;
- approval status;
- origin and evidence;
- optional classification, severity, owner, tags, and relations;
- human-readable content.

Example:

```yaml
id: localization.supported-locales
type: knowledge
revision: 2
status: approved
classification: fact
origin: human
owner: product
sources:
  - src/i18n/config.ts
tags:
  - localization
  - frontend
```

### 4.2 Core Brain Item Types

- `knowledge` — facts and project understanding;
- `question` — information that must be discovered or clarified;
- `contract` — invariants and boundaries that must not be violated;
- `decision` — accepted reasoning and alternatives;
- `playbook` — execution guidance for a type of work;
- `verification` — criteria and methods for validating the result.

Risk, assumptions, recommendations, and similar concepts are metadata classifications rather than additional core types.

### 4.3 Document

A Document is a human-readable Markdown container for Brain Items.

The Document is the canonical authoring representation.

### 4.4 Work/Task Package

The engine accepts a normalized internal package rather than external provider-specific objects.

The final name remains under RFC discussion.

```yaml
request:
  title: Fix localization of table headers
  description: Table headers remain Russian after switching locale.

intent:
  declared: bugfix
  detected: localization_bugfix

project:
  repository: mrAlexrti/3dkidShop
  branch: redesign-3dkid-v2
  revision: commit-sha

constraints:
  - do_not_change_visual_design
  - use_existing_localization_system

origin:
  adapter: cli
```

### 4.5 Context Package

The Context Package contains:

- detected intent and domains;
- risk level;
- execution state;
- known facts;
- assumptions;
- missing answers;
- conflicts;
- critical and required contracts;
- selected playbook;
- affected areas;
- allowed and forbidden actions;
- verification criteria;
- selection explanations;
- supporting knowledge available on demand.

## 5. Knowledge Storage

Brain Items are stored in Markdown documents using explicit boundaries:

````markdown
<!-- brain:item:start -->
```yaml
id: localization.no-hardcoded-ui
type: contract
revision: 1
status: approved
severity: high
```

User-facing text must not be hardcoded in UI components.
<!-- brain:item:end -->
````

The engine may generate:

```text
.brain/.index/items.json
```

The index is derived, reproducible, disposable, and never manually edited.

## 6. Revision Model

Brain Item identity is stable. Revisions are immutable.

```yaml
id: localization.supported-locales
revision: 2
previous_revision: 1
status: approved
decision_ref: decision.localization.remove-ru
```

Git provides historical storage for the MVP.

## 7. Authority and Conflicts

Authority depends on the knowledge domain.

| Knowledge domain | Primary authority |
|---|---|
| Business rules | Approved contracts and decisions |
| Current implementation | Source code and configuration |
| Current work intent | Work/Task Package |
| Historical rationale | Decisions and ADRs |
| Discovered technical facts | Scanner output with evidence |

The engine distinguishes:

- how the system should work;
- how the system works now;
- how the requester wants it to change.

Conflicts are explicit outputs, not silent resolutions.

## 8. Context Retrieval

```text
Package
  ↓
Intent and domain detection
  ↓
Deterministic selection
  ↓
Required contracts, questions, playbooks, and verification
  ↓
Relation expansion
  ↓
Optional semantic enrichment
  ↓
Ranking with explanations
  ↓
Tiered Context Package
```

Semantic retrieval may improve recall, but cannot change approval status, override contracts, resolve conflicts, or convert assumptions into facts.

## 9. Tiered Context

### Tier 1 — Critical

Blocking questions, critical contracts, source conflicts, forbidden actions, and execution state.

### Tier 2 — Required

Primary knowledge, selected playbook, affected areas, and verification criteria.

### Tier 3 — Supporting

Related decisions, historical context, similar implementations, and non-critical risks.

### Tier 4 — Available on Demand

Knowledge exposed by ID and retrieval condition without immediate inclusion.

## 10. Execution States

- `ready`;
- `investigation_required`;
- `clarification_required`;
- `blocked`.

Example:

```yaml
execution:
  status: clarification_required
  allowed:
    - read_repository
    - search_code
    - prepare_plan
    - ask_questions
  forbidden:
    - modify_code
    - commit
    - deploy
```

## 11. Learning Model

AI agents may propose new knowledge.

They do not automatically approve critical project memory.

```text
Task execution
      ↓
New observation
      ↓
Knowledge Proposal
      ↓
Evidence and conflict validation
      ↓
Approval policy
      ↓
New Brain Item revision
```

## 12. Initial Components

```text
brain_engine/
├── domain/
│   ├── brain_item.py
│   ├── work_package.py
│   ├── context_package.py
│   └── proposal.py
├── parser/
│   └── markdown_items.py
├── index/
│   └── item_index.py
├── routing/
│   ├── intent.py
│   ├── questions.py
│   └── retrieval.py
├── execution/
│   └── policy.py
├── validation/
│   └── validator.py
└── cli/
    └── app.py
```

## 13. Initial Commands

```bash
brain init
brain context "<task>"
brain validate
```

Later:

```bash
brain scan
brain review
brain doctor
brain diff
brain learn
brain serve-mcp
```

## 14. Non-Goals for the First MVP

- hosted cloud platform;
- visual dashboard;
- full graph database;
- automatic approval of business knowledge;
- support for every language and framework;
- mandatory external embeddings;
- marketplace;
- custom foundation model.

## 15. First Validation Experiment

The first controlled experiment will use a real localization defect in `3dkidShop`.

Two runs will use the same repository revision, AI model, prompt, and independent workspaces. One branch will have Brain and one will not.

The comparison will evaluate correctness, architecture compliance, reuse of existing localization infrastructure, unsupported assumptions, unnecessary changes, build result, and corrective iterations.
