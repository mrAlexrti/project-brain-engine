# RFC-0002: Question-Driven Context Generation

- **Status:** Draft
- **Date:** 2026-07-12

## Summary

Project Brain should not begin by retrieving documents.

It should begin by determining which questions must be answered for the requested work.

## Proposed Flow

```text
Input Package
      ↓
Intent and domain classification
      ↓
Question Set selection
      ↓
Answer resolution from approved Brain Items
      ↓
Repository investigation for technical facts
      ↓
Missing and conflicting answer detection
      ↓
Execution policy
      ↓
Context Package
```

## Question Definition

```yaml
id: localization.question.supported-locales
type: question
revision: 1
status: approved

applies_to:
  intents:
    - localization_bugfix
    - localization_feature

severity: critical

blocking:
  modify_code: true
  investigation: false

question: Which locales must remain supported?

answer_from:
  - localization.supported-locales
```

## Answer States

- `resolved`;
- `inferred`;
- `conflicting`;
- `missing`;
- `not_applicable`.

## Open Questions

1. Should Question Sets be Brain Items, documents, or both?
2. Can Questions reference executable repository checks?
3. How should generic and domain-specific Question Sets merge?
4. How should the engine detect that a question is no longer relevant?
5. When may a code-derived answer be treated as authoritative?

## Initial Experiment

Use the `3dkidShop` localization defect.

Expected questions:

- Which locales are supported?
- What is the translation source of truth?
- What is the fallback locale?
- Which pages reproduce the defect?
- Is locale switching expected without reload?
- Which implementation and design areas are protected?
