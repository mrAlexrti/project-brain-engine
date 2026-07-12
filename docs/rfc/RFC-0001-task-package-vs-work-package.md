# RFC-0001: Task Package vs Work Package

- **Status:** Open
- **Date:** 2026-07-12

## Problem

The engine needs one normalized input object.

`Task Package` is clear for implementation tasks but may be too narrow for pull request review, architecture analysis, security audit, repository research, migration planning, and incident investigation.

`Work Package` is broader but less familiar and may sound like project-management terminology.

## Options

### Task Package

Advantages:

- familiar;
- concise;
- maps naturally to issues and tickets.

Risk:

- may exclude non-task workflows conceptually.

### Work Package

Advantages:

- covers implementation, review, research, and audit;
- better represents a general unit of engineering work.

Risk:

- less immediately obvious;
- possible confusion with formal project-management standards.

### Neutral Internal Name

Possible alternatives:

- `RequestPackage`;
- `EngineeringRequest`;
- `BrainRequest`.

## Proposed Experiment

Implement the schema behind a neutral internal interface and test it with:

- localization bug fix;
- pull request review;
- architecture assessment;
- security audit.

## Decision Criteria

The chosen term should describe all expected engine inputs, remain understandable without documentation, avoid provider coupling, and work naturally in CLI, API, and MCP contexts.
