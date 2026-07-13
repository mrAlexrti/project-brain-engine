# Project Brain Engine

Project Brain Engine is a model-independent, question-driven project knowledge runtime. It accepts a task and trusted, project-owned Brain knowledge and produces a minimum sufficient Context Package.

## Application-first start

```bash
pip install -e ".[dev]"
brain app
```

The application binds to `127.0.0.1`, runs entirely on the developer's machine, and opens the default browser. It has no accounts, cloud backend, telemetry, analytics, external uploads, remote JavaScript, model calls, or bundled agent. Standalone native packaging is future work.

Connect a local Git repository, inspect stable metadata, initialize or select Brain knowledge, freeze a task and Context Package, create two neutral run packages, capture evidence, lock a neutral evaluation, reveal treatment, and finalize an integrity manifest.

Raw evidence can contain private code and project rules. Keep experiment output outside the source repository and select the appropriate privacy mode.

## CLI

The CLI remains a deterministic automation, CI, and advanced-user interface:

```bash
brain version
brain init --path .
brain validate .brain
brain context "Fix the checkout defect" --format yaml
brain experiment --help
brain app --host 127.0.0.1 --port 8765 --no-open --data-dir ./local-data
```

`brain-app` is also available as a direct launcher. A busy default port causes selection of a safe free local port. A non-loopback host is allowed only when explicitly passed and prints a warning.

Original English, Russian, Ukrainian, mixed Cyrillic/Latin, and other valid UTF-8 text is preserved. Matching uses deterministic Unicode normalization and casefolding internally; automatic translation is never performed. Generated knowledge starts as `proposed`, and approval remains an explicit owner action.

## Documentation

- [Local application](docs/APPLICATION.md)
- [Brain initialization](docs/BRAIN_INIT.md)
- [Experiment mode](docs/EXPERIMENT_MODE.md)
- [Multilingual support](docs/MULTILINGUAL_SUPPORT.md)
- [Privacy](docs/PRIVACY.md)
- [External tester guide](docs/EXTERNAL_TESTER_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)

Apache-2.0 licensed.
