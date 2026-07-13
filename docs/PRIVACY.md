# Privacy and Safety

The application is local by default and binds only to `127.0.0.1`. It has no telemetry, analytics, accounts, remote assets, uploads, model calls, or remote API calls. Explicit non-loopback binding prints a warning.

Privacy modes are `private`, `anonymized-results-only`, and `public`. Raw evidence may include source patches, business rules, absolute paths, user or machine names, agent reports, and command output. Private mappings and local source paths live under `evidence/private`.

Do not record secrets. Environment-variable collection is names-only. Experiment paths are resolved and checked; output inside the source repository is refused. Git is invoked with argument lists and `shell=False`. Verification is never automatic; the runner accepts only structured executable/subcommand combinations from a conservative test-and-lint allowlist.

Every state-changing application route requires an exact same-origin `Origin` header and a matching CSRF form token/cookie. Cookies use `SameSite=Strict`; GET routes remain read-only.

Private mode does not automatically create a public export. No command publishes, commits, pushes, deploys, or accesses production.
