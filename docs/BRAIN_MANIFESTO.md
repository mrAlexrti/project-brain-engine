# Project Brain Engine Manifesto

> Project Brain Engine does not make AI smarter. It makes software projects understandable.

## Purpose

AI coding agents can already generate code, refactor systems, and fix defects. Their main limitation is not syntax. It is project understanding.

Project Brain Engine exists to give any AI agent a structured, trusted, project-owned knowledge layer.

## Core Belief

The goal of AI-assisted development is not to generate more code.

The goal is to make better engineering decisions.

A correct implementation begins before coding. It begins when the system identifies what must be understood, what is already known, what is missing, and what must not be violated.

## The Four Foundations

### Knowledge

What the project already knows: architecture, business rules, terminology, component relationships, operational constraints, and accepted engineering decisions.

### Questions

What must be clarified before work can begin.

A task is not ready merely because it is written. It is ready when its critical questions have trustworthy answers.

### Contracts

What must remain true: invariants, protected behaviour, allowed changes, forbidden changes, compatibility requirements, and review focus.

A contract is stronger than a prompt.

### Playbooks

How work should be performed: features, bug fixes, refactoring, localization, security, database changes, API changes, and UI changes.

## Principles

1. **Project memory belongs to the project.**
2. **Knowledge is more durable than prompts.**
3. **Every important task begins with questions.**
4. **Facts, assumptions, conflicts, and unknowns must remain separate.**
5. **Missing critical knowledge must restrict unsafe actions.**
6. **Important knowledge must have one authoritative source per domain.**
7. **Contracts outrank convenience.**
8. **Evolution is preferred over unnecessary rewrites.**
9. **The system must remain model-independent.**
10. **Human authority over critical project memory must remain explicit.**

## Trust Model

```yaml
status: proposed | approved | deprecated
origin: human | code-scan | imported | ai-generated
confidence: 0.0-1.0
owner: person-or-team
sources:
  - path-or-reference
last_verified: YYYY-MM-DD
```

Generated knowledge is never automatically equivalent to approved knowledge.

## Task Understanding Flow

```text
Work request
  ↓
Input adapter
  ↓
Task/Work Package
  ↓
Intent and risk classification
  ↓
Required question set
  ↓
Known answers from trusted project knowledge
  ↓
Missing and conflicting answers
  ↓
Human clarification or repository investigation
  ↓
Trusted Context Package
  ↓
Implementation
  ↓
Contract-aware review
  ↓
Knowledge proposals
```

## Context Principle

The goal is not maximum context.

The goal is **minimum sufficient trusted context**.

## What Project Brain Is Not

Project Brain is not a generic documentation generator, a giant prompt file, a model-specific instruction format, or a guarantee that AI output is correct.

## Mission

> Make project understanding portable, explicit, trusted, and independent of any single AI agent.
