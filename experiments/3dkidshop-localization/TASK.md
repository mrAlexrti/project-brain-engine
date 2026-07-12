# Canonical Task Prompt

Use the text between the delimiters verbatim for both runs. Do not include the delimiters or surrounding instructions in the agent prompt.

<!-- CANONICAL TASK START -->
Reproduce and fix the storefront localization defect where some table column labels remain in Russian after the user switches the locale to Ukrainian or English.

Inspect the repository and its existing behavior before implementing the fix. Reuse the project's existing localization mechanism. Preserve the current design and all behavior outside this defect; do not introduce an unrelated redesign.

Perform the relevant build, tests, lint, and/or manual verification available in the project. In your final report, describe the files changed, your reasoning, the verification performed and its results, and any remaining uncertainty.

Do not commit or push changes.
<!-- CANONICAL TASK END -->
