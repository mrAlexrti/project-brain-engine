# RFC-0003: Context Package

- **Status:** Draft
- **Date:** 2026-07-12

## Summary

A Context Package is the structured output of Project Brain Engine.

It must be model-independent, explainable, compact, and safe to serialize through CLI, API, or MCP.

## Proposed Schema

```yaml
context_package:
  schema_version: 0.1

  request:
    title: Fix localization of table headers

  classification:
    intent: localization_bugfix
    domains:
      - localization
      - frontend
    risk: medium

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

  critical:
    questions:
      - item_id: localization.question.supported-locales
        answer_status: missing

    contracts:
      - item_id: localization.no-hardcoded-ui

    conflicts: []

  required:
    knowledge:
      - item_id: localization.translation-source

    playbooks:
      - item_id: playbook.localization-change

    verification:
      - item_id: verification.locale-switching

  supporting:
    decisions: []
    examples: []

  available_on_demand:
    - item_id: architecture.frontend-boundaries
      fetch_when: change crosses localization infrastructure boundary

  retrieval:
    selected:
      - item_id: localization.no-hardcoded-ui
        reasons:
          - matched_domain: localization
          - required_by_playbook: playbook.localization-change
```

## Required Properties

The package must:

- separate facts, assumptions, conflicts, and unknowns;
- expose execution restrictions;
- preserve Item IDs and revisions;
- explain retrieval;
- remain serializable;
- support context budgeting;
- avoid provider-specific prompt instructions.

## Open Questions

1. Should the package contain full Item content or references plus selected excerpts?
2. How should content budgets be represented?
3. Should the package include a generated agent prompt?
4. How should sensitive Items be redacted?
5. How should a package bind to a repository commit?
6. How should stale knowledge be represented?

## Initial Output Formats

- human-readable console;
- Markdown;
- YAML;
- JSON.
