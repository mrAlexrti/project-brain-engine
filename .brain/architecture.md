<!-- brain:item:start -->
```yaml
id: architecture.hybrid-knowledge-model
type: decision
revision: 1
status: approved
domains: [architecture, knowledge]
keywords: [architecture, model, document, item]
sources: [docs/adr/ADR-0001-hybrid-knowledge-model.md]
```

Brain Items are atomic knowledge units; Markdown Documents are human-readable containers for them.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: architecture.input-agnostic-engine
type: decision
revision: 1
status: approved
domains: [architecture, context]
keywords: [architecture, adapter, input, package]
sources: [docs/adr/ADR-0003-input-agnostic-engine.md]
```

Adapters normalize external inputs. The core accepts a neutral package and returns a Context Package.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: architecture.stable-item-identity
type: decision
revision: 1
status: approved
domains: [architecture, knowledge]
keywords: [architecture, identity, revision]
sources: [docs/adr/ADR-0007-stable-identities-and-revisions.md]
```

Logical Item identity is stable, revisions are immutable, and approval selects the active truth.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: architecture.hybrid-context-retrieval
type: decision
revision: 1
status: approved
domains: [architecture, context]
keywords: [architecture, context, retrieval, deterministic]
sources: [docs/adr/ADR-0009-hybrid-context-retrieval.md]
```

Retrieval starts with explainable deterministic signals; optional semantics may only expand recall.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: architecture.tiered-context-package
type: decision
revision: 1
status: approved
domains: [architecture, context]
keywords: [architecture, context, tier, package]
sources: [docs/adr/ADR-0010-tiered-context-package.md]
```

Context is divided into Critical, Required, Supporting, and Available-on-demand tiers.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: architecture.proposal-first-learning
type: decision
revision: 1
status: approved
domains: [architecture, knowledge]
keywords: [architecture, proposal, learning, approval]
sources: [docs/adr/ADR-0011-proposal-first-learning.md]
```

AI agents may propose knowledge, but authority determines what becomes approved project memory.
<!-- brain:item:end -->
