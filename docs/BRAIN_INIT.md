# Brain Initialization

Interactive: `brain init --path /path/to/project`.

Deterministic automation:

```bash
brain init --path /path/to/project --non-interactive \
  --project-name "Example" --project-purpose "Owner supplied purpose" \
  --primary-technology "Python" --language "uk"
```

Initialization refuses a non-empty `.brain` directory and intentionally has no force option. It creates `.brain/PROJECT_INTAKE.md`, a human README, type directories, and one proposed Item per Markdown file. Output is UTF-8 without a BOM, written atomically, and validated before success is reported.

No generated Item is approved. Review exact content and sources, then approve trusted knowledge explicitly. Never put environment-variable values or other secrets in intake; record variable names only.
