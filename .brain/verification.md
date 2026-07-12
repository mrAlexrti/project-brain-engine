<!-- brain:item:start -->
```yaml
id: verification.python-quality
type: verification
revision: 1
status: approved
domains: [python, testing]
keywords: [python, pytest, ruff, test, quality]
sources: [pyproject.toml]
```

Run `python -m pytest` and `python -m ruff check .`; both commands must succeed.
<!-- brain:item:end -->

<!-- brain:item:start -->
```yaml
id: verification.brain-validation
type: verification
revision: 1
status: approved
domains: [validation, knowledge]
keywords: [brain, validate, validation]
sources: [docs/ROADMAP.md, docs/ARCHITECTURE.md]
```

Run `brain validate .brain` and require zero validation errors.
<!-- brain:item:end -->
