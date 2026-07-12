# Run A Record — No Context Package

Official experiment record. The complete comparison and limitations are documented in RESULTS.md.

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

