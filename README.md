# 🧠 Project Brain Engine

> **The knowledge layer for AI-assisted software development**

Project Brain Engine (PBE) is an open standard and reference implementation for organizing project knowledge, engineering decisions, contracts, questions, and workflows so that **any AI coding agent** can understand a software project—not only its source code.

Project Brain does not try to make AI models smarter.

It makes software projects understandable.

## Why

Modern AI coding agents can generate code, refactor systems, and fix defects. Their main limitation is project understanding.

They often do not know:

- why the architecture exists in its current form;
- which business rules are critical;
- which parts of the system must remain stable;
- what was tried before and why it failed;
- which questions must be answered before implementation begins;
- which assumptions are safe and which are dangerous.

Project Brain Engine provides a structured, trusted, project-owned knowledge layer between a software project and any AI agent.

## Core Flow

```text
External tool or user request
            ↓
      Input adapter
            ↓
     Work/Task Package
            ↓
   Project Brain Engine
            ↓
      Context Package
            ↓
Claude / Codex / Gemini / Copilot / future agents
```

## Core Concepts

- **Brain Item** — the logical unit of project knowledge.
- **Document** — a human-readable container for Brain Items.
- **Question Set** — questions that must be answered before a class of work begins.
- **Contract** — an invariant or boundary that must not be violated.
- **Playbook** — the recommended execution strategy for a type of work.
- **Context Package** — the minimum sufficient trusted context for a task.
- **Knowledge Proposal** — an AI-generated suggestion to update project memory.

## Initial Product Direction

```bash
brain init
brain context "<task>"
brain validate
```

Planned:

```bash
brain scan
brain review
brain doctor
brain diff
brain learn
```

## Documentation

- [Manifesto](docs/BRAIN_MANIFESTO.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture Decision Records](docs/adr/)
- [Requests for Comments](docs/rfc/)

## Current Status

🚧 **Architecture and research phase**

The first reference implementation will be validated on real software projects, beginning with `3dkidShop`.

## Mission

> **Project Brain doesn't make AI smarter.**
>
> **It makes software projects understandable.**

## License

Apache License 2.0
