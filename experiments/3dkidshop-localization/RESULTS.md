# 3dkidShop Localization A/B Experiment — Final Evaluation

## Outcome

**Hypothesis outcome:** supported, with a modest observed effect.

Both official runs produced valid implementations using the repository's existing localization mechanism. Run B, which received the Project Brain Context Package, achieved a slightly higher score because it performed more explicit localization verification, localized the complete table-heading surface, handled the known build limitation more precisely, and reported project uncertainties more clearly.

The observed difference is small and applies only to this repository, defect, baseline, model configuration, and pair of stochastic Codex sessions. It is not evidence of general effectiveness by itself.

## Experiment identity

| Field | Value |
|---|---|
| Target repository | mrAlexrti/3dkidShop |
| Baseline branch | redesign-3dkid-v2 |
| Baseline commit | aa8e630e6ea3afe4e6dac0c124e997df71c7253c |
| Project Brain Engine commit | b52c658396983f2c19a4a2128b00465fde4158cb |
| Model | gpt-5.6-sol |
| Reasoning effort | medium |
| Codex CLI | 0.144.1 |
| Node.js | v24.16.0 |
| npm | 11.13.0 |
| Maximum time per run | 30 minutes |
| Dependency installation | npm ci --legacy-peer-deps |
| Operating system | Windows 11 Home 10.0.26200 64-bit |

## Controlled conditions

Both official runs used:

- the same complete canonical task;
- the same baseline commit;
- clean isolated workspaces;
- the same model and reasoning effort;
- the same Codex version;
- the same dependency state;
- the same permissions and approval behavior;
- the same network policy;
- fresh Codex sessions;
- no clarification responses or corrective iterations.

Run A received only the canonical task and repository.

Run B received the same canonical task and repository plus the archived Project Brain Context Package.

## Baseline

Both workspaces had the same baseline results:

- dependency installation with `npm ci --legacy-peer-deps`: passed;
- `npm run lint`: passed;
- production build compilation: passed;
- production build page-data collection: failed because `DATABASE_URL` was absent.

The missing `DATABASE_URL` was established before both official runs and is not a regression introduced by either implementation.

## Run A — No Context Package

### Implementation

Changed files:

- `src/app/admin/orders/[id]/page.tsx`
- `src/lib/i18n.ts`

Diff size:

- 20 insertions;
- 6 deletions;
- 2 tracked files modified.

Implementation behavior:

- added `admin.orderItems` translations for Ukrainian and English;
- localized the four table column labels;
- reused server-side `getT()`;
- preserved the existing `Promise.all` structure;
- did not localize the adjacent `Товари` section heading.

Verification reported:

- `npm run lint`: passed;
- `npx tsc --noEmit`: passed;
- `git diff --check`: passed;
- production build compilation and type validation: passed;
- page-data collection failed at the known missing-database baseline limitation;
- browser-level locale switching was not available.

Final working tree also contained an untracked `tsconfig.tsbuildinfo` file generated during type checking.

Patch SHA-256:

`D0945CF2257DEB0FC5564B916C73FF6FB7F29E2E3CD82548E268B5723F94C67E`

### Score

| Category | Score | Evidence and deductions |
|---|---:|---|
| Functional correctness | 27 / 30 | Four affected columns use `getT()` values with UA and EN resources; default mechanism preserved; available checks passed. No direct browser verification of switching behavior. |
| Localization architecture compliance | 20 / 20 | Existing typed translation resources and `getT()` were reused; no parallel mechanism or new hardcoded column labels. |
| Scope discipline | 10 / 10 | Only the two relevant tracked files were modified; no unrelated redesign or dependency changes. |
| Verification quality | 9 / 15 | Lint, type checking, diff check, and partial build verification were performed. No direct UA/EN/default/switching browser verification. |
| Unsupported assumptions | 9 / 10 | Remaining verification uncertainty was reported, but the claim that only two intended files were present did not mention the generated untracked `tsconfig.tsbuildinfo`. |
| Maintainability and code quality | 10 / 10 | Clear, minimal implementation that preserved the existing concurrent `Promise.all` structure. |
| Execution efficiency | 4 / 5 | Completed within the limit with no prompts, questions, or corrections. One unnecessary generated working-tree artifact remained. |
| **Raw subtotal** | **89 / 100** | |
| Critical-failure cap | None | No applicable critical failure. |
| **Final score** | **89 / 100** | |

## Run B — With Project Brain Context Package

### Implementation

Changed files:

- `src/app/admin/orders/[id]/page.tsx`
- `src/lib/i18n.ts`

Diff size:

- 23 insertions;
- 6 deletions;
- 2 tracked files modified.

Implementation behavior:

- added page-specific `admin.orderDetail` translations for Ukrainian and English;
- localized the four table columns;
- additionally localized the adjacent `Товари / Items` section heading;
- reused server-side `getT()` and the existing locale-cookie design;
- replaced the previous parallel `Promise.all` with sequential awaits.

Verification reported:

- `npm run lint`: passed;
- `git diff --check`: passed;
- focused UA/EN translation-shape and value assertion: passed;
- production build compilation, type checking, and linting: passed;
- page-data collection failed at the documented missing-database baseline limitation;
- browser-level locale switching was not available.

Patch SHA-256:

`28E52DAE34D41556DB0236FB786198EBCFA2EF7BCB2EED303C7B7D3FA74F8F42`

### Score

| Category | Score | Evidence and deductions |
|---|---:|---|
| Functional correctness | 27 / 30 | Four affected columns and the adjacent heading use localized values; UA and EN resources exist; available checks passed. No direct browser verification of switching behavior. |
| Localization architecture compliance | 20 / 20 | Correctly reused `i18n.ts`, `getT()`, supported locales, and the existing server cookie mechanism. |
| Scope discipline | 8 / 10 | Changes remained in the affected area, but replacing `Promise.all` with sequential awaits was an unnecessary refactor. |
| Verification quality | 11 / 15 | Lint, diff check, build-stage checks, and a focused UA/EN shape/value assertion were performed. No browser verification of UA, EN, default, and switching behavior. |
| Unsupported assumptions | 10 / 10 | Known environment limitations and unresolved localization ownership were accurately reported without presenting them as verified facts. |
| Maintainability and code quality | 9 / 10 | `admin.orderDetail` is clear and page-specific, but sequential awaits are slightly less efficient than the original concurrent structure. |
| Execution efficiency | 5 / 5 | Completed within the limit with no permission prompts, clarification questions, corrective iterations, or unnecessary files. |
| **Raw subtotal** | **90 / 100** | |
| Critical-failure cap | None | No applicable critical failure. |
| **Final score** | **90 / 100** | |

## Side-by-side comparison

| Metric | Run A | Run B |
|---|---:|---:|
| Final score | 89 | 90 |
| Tracked files changed | 2 | 2 |
| Insertions | 20 | 23 |
| Deletions | 6 | 6 |
| Permission prompts | 0 | 0 |
| Clarification questions | 0 | 0 |
| Corrective iterations | 0 | 0 |
| Exact elapsed time | Not recorded | Not recorded |
| Completed under 30-minute limit | Yes | Yes |
| Direct browser locale verification | No | No |
| Focused UA/EN assertion | No | Yes |
| Untracked generated artifact | `tsconfig.tsbuildinfo` | None |

## Main observed differences

Run A produced the narrower implementation and preserved the existing concurrent parameter/translation retrieval.

Run B demonstrated greater context awareness:

- used a page-specific translation group;
- localized the complete heading surface rather than only the four columns;
- performed an explicit UA/EN translation assertion;
- correctly treated the missing database as a documented baseline limitation;
- explicitly reported localization ownership and environment uncertainty.

Run B also introduced a minor unnecessary refactor by replacing `Promise.all` with sequential awaits.

## Protocol deviations and limitations

An earlier pilot Run A accidentally received a shortened prompt. That pilot prompt and patch were archived separately and excluded from official scoring.

The official Run A and Run B both used the complete canonical task. Equality between the official Run A supplied prompt and `canonical-task.txt` was confirmed after line-ending normalization.

Exact start times were not recorded, so elapsed duration cannot be reconstructed. Both runs were directly observed to complete within the shared 30-minute limit.

Node.js, npm, Codex CLI, model, and reasoning effort were recorded in shared experiment metadata rather than separately inside each official run directory.

The operator and evaluator knew the treatment mapping before final scoring. Full evaluator blinding was therefore not achieved.

Neither run had access to a configured database-backed browser environment, so actual locale switching on a populated order-detail page was not directly verified.

This was one defect, one repository baseline, one model configuration, and one pair of stochastic sessions. A one-point result difference should not be generalized.

## Final conclusion

**Hypothesis outcome: supported.**

The Project Brain Context Package produced a modest observable improvement in verification discipline, context-aware reporting, and completeness of the localized surface. It did not produce a radically different implementation: both runs independently found the correct files, reused `getT()`, added matching Ukrainian and English resources, and produced functionally credible fixes.

The result supports continuing the experiment across additional paired repetitions and defects, but does not establish broad causal effectiveness.

## Recommended next experiment

Repeat at least three additional paired runs on the same frozen baseline while:

- counterbalancing whether the Context Package run executes first or second;
- recording exact start and finish times automatically;
- archiving complete Codex transcripts or structured command logs;
- using neutral result labels until initial scoring is locked;
- adding an isolated test fixture or database snapshot for direct browser verification;
- keeping evaluator treatment mapping hidden until initial scores are recorded.
