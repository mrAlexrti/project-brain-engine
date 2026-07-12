# ADR-0003: Input-Agnostic Brain Engine

- **Status:** Accepted
- **Date:** 2026-07-12

## Context

Project Brain must work with GitHub, Jira, CLI tools, IDEs, MCP clients, and future systems without embedding provider-specific behaviour into the core engine.

## Decision

External systems are handled by adapters.

The core engine accepts one normalized internal package and returns a Context Package.

The final name of the input package remains open under RFC-0001.

## Consequences

- integrations remain replaceable;
- the core domain can be tested without external services;
- adapters own provider-specific mapping;
- package schema stability becomes important.
