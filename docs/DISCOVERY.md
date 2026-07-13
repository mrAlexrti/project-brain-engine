# Deterministic Project Discovery

Project discovery inspects a bounded selection of files from an exact committed Git tree. It
does not execute repository code or commands, load project-local executable configuration,
follow symlinks, read untracked files, use a network, or retain environment-template values.

## Confidence rules

- `high`: an explicit manifest field, dependency, script, lockfile, or directly documented
  purpose supplies the value;
- `medium`: two or more consistent repository markers supply the value;
- `low`: only a filename, directory, or single documentation marker supports the inference.

Confidence describes evidence quality. It never grants authority. Findings remain unreviewed,
proposals always start as `proposed`, conflicts remain unresolved, and only an explicit owner
action can approve a resulting Brain Item.

Each scan creates a new immutable numbered discovery revision under application-managed data.
Controlled artifacts are hashed from their exact stored bytes. A report becomes stale whenever
the repository HEAD differs from the SHA recorded by that revision.
