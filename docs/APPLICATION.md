# Local Application

Run `brain app`. The default URL is `http://127.0.0.1:8765/`; the actual URL is printed. Use `--no-open`, `--data-dir PATH`, `--host HOST`, or `--port PORT` as needed. `brain-app` exposes the same launcher options.

The interface is a local operator console, not a hosted service. It uses server-rendered HTML, standard forms, locally packaged CSS, and a small local JavaScript confirmation helper. No CDN or frontend build system is involved.

The flow is: connect project → review stable repository metadata → complete project intake → initialize an application-managed Brain outside the repository → list, create, edit, and explicitly approve Brain Items → review validation and answer Questions → preview and freeze Context → run experiment preflight → enter evaluator-only Ground Truth → create isolated worktrees and neutral packages → operate Run 1/Run 2 → capture evidence → score and lock evaluation → reveal mapping → finalize.

GET routes are read-only. State-changing actions use POST with strict same-origin Origin and CSRF validation. The normal experiment screen uses only `result-1` and `result-2` and cannot load the private treatment map.

Context freezes are immutable, numbered revisions. Each snapshot records its timestamp plus SHA-256 values calculated from the exact stored task and Context bytes. Regeneration requires an explicit new-revision confirmation and preserves every earlier snapshot. Experiment creation reached from preflight automatically binds the selected repository, application-managed Brain, task, and latest frozen Context revision.

The current UI accepts repository paths as text because browsers cannot safely expose arbitrary local directory paths. It never runs an agent and never runs verification automatically.
