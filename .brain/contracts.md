<!-- brain:item:start -->
```yaml
id: contract.no-silent-conflict-resolution
type: contract
revision: 1
status: approved
severity: critical
domains: [architecture, knowledge, context]
keywords: [conflict, authority, architecture]
sources: [docs/adr/ADR-0006-authority-domains-and-conflicts.md]
```

Conflicts between authoritative sources must be surfaced explicitly and never resolved silently.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: contract.critical-knowledge-human-approval
type: contract
revision: 1
status: approved
severity: critical
domains: [architecture, knowledge]
keywords: [approval, critical, knowledge]
sources: [docs/adr/ADR-0011-proposal-first-learning.md, docs/BRAIN_MANIFESTO.md]
```

Generated critical project knowledge must not become approved without the applicable authority policy.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: contract.deterministic-core
type: contract
revision: 1
status: approved
severity: critical
domains: [architecture, context]
keywords: [deterministic, retrieval, context]
sources: [docs/adr/ADR-0009-hybrid-context-retrieval.md]
```

Deterministic retrieval establishes trust; semantic signals cannot override approval or contracts.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: contract.critical-context-is-never-truncated
type: contract
revision: 1
status: approved
severity: critical
domains: [architecture, context]
keywords: [critical, context, budget, truncate]
sources: [docs/adr/ADR-0010-tiered-context-package.md]
```

Context budgets may reduce Supporting context but must never remove Critical context.
<!-- brain:item:end -->
