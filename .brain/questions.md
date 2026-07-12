<!-- brain:item:start -->
```yaml
id: question.change.project-goal
type: question
revision: 1
status: approved
severity: high
applies_to:
  intents: [architecture_change, bugfix, feature]
answer_mode: request
blocking: {modify_code: true, commit: true, deploy: true}
domains: [project]
keywords: [goal, purpose]
sources: [docs/BRAIN_MANIFESTO.md]
```

What project goal and trusted outcome should this change preserve?
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: question.change.affected-contracts
type: question
revision: 1
status: approved
severity: critical
applies_to:
  intents: [architecture_change, bugfix, feature]
answer_mode: request
blocking: {modify_code: true, commit: true, deploy: true}
domains: [architecture]
keywords: [contract, change]
sources: [docs/BRAIN_MANIFESTO.md, docs/ARCHITECTURE.md]
```

Which approved contracts constrain the requested change?
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: question.change.verification
type: question
revision: 1
status: approved
severity: high
applies_to:
  intents: [architecture_change, bugfix, feature]
answer_mode: knowledge
answer_from: [verification.python-quality, verification.brain-validation]
blocking: {commit: true, deploy: true}
domains: [testing, validation]
keywords: [test, verification, quality]
sources: [docs/ARCHITECTURE.md, docs/ROADMAP.md]
```

How will the requested change be verified against project expectations?
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: question.architecture.existing-decisions
type: question
revision: 1
status: approved
severity: critical
applies_to:
  intents: [architecture_change]
  domains: [architecture]
answer_mode: knowledge
answer_from: [architecture.hybrid-knowledge-model, architecture.input-agnostic-engine]
blocking: {modify_code: true, commit: true, deploy: true}
domains: [architecture]
keywords: [architecture, decision, adr]
sources: [docs/ARCHITECTURE.md, docs/adr/ADR-0004-architecture-governance.md]
```

Which accepted architectural decisions govern this change?
<!-- brain:item:end -->
