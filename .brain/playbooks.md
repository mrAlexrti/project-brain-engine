<!-- brain:item:start -->
```yaml
id: playbook.architecture-change
type: playbook
revision: 1
status: approved
applies_to:
  intents: [architecture_change]
  domains: [architecture]
required_questions: [question.change.project-goal, question.change.affected-contracts, question.architecture.existing-decisions, question.change.verification]
required_items: [contract.no-silent-conflict-resolution, contract.critical-knowledge-human-approval, contract.deterministic-core, contract.critical-context-is-never-truncated, verification.brain-validation]
domains: [architecture]
keywords: [architecture, adr, design]
sources: [docs/ARCHITECTURE.md, docs/adr/ADR-0004-architecture-governance.md]
```

Review accepted decisions and contracts, preserve explicit authority, then validate documentation and Brain Items.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: playbook.python-change
type: playbook
revision: 1
status: approved
applies_to:
  intents: [feature, bugfix]
  domains: [python, cli, validation, testing]
required_questions: [question.change.project-goal, question.change.verification]
required_items: [contract.deterministic-core, verification.python-quality, verification.brain-validation]
domains: [python, cli, validation, testing]
keywords: [python, pytest, ruff, cli]
sources: [docs/ROADMAP.md, pyproject.toml]
```

Make focused Python changes, preserve deterministic behaviour, and run pytest, Ruff, and Brain validation.
<!-- brain:item:end -->
