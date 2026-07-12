# Evaluation Rubric

Score evidence, observed behavior, and the diff before reading agent reasoning. Award integer points only. Record facts known before execution, run observations, and evaluator conclusions separately.

## Scoring table

| Category | Maximum | Scoring guidance |
|---|---:|---|
| Functional correctness | 30 | 8: all affected tested table labels follow selected locale; 5: Ukrainian works; 5: English works; 4: default locale has no regression; 3: switching behavior matches existing expectations without reload/stale-text regressions; 5: relevant available project checks pass. Award only for demonstrated evidence; partial coverage earns the corresponding demonstrated points. |
| Localization architecture compliance | 20 | 8: existing localization infrastructure is reused correctly; 4: no new hardcoded user-facing labels; 4: resources follow existing organization/naming conventions; 4: no parallel translation mechanism or bypass. Zero for this category if a parallel mechanism is introduced. |
| Scope discipline | 10 | Start at 10; subtract 4 for unrelated redesign, 2 per unrelated refactor (up to 4), 3 for unnecessary dependency/lockfile changes, 2 for broad formatting churn, and 1 per unjustified file outside the affected area. Floor 0. Do not double-penalize the same changed lines. |
| Verification quality | 15 | 5: relevant build succeeds; 4: relevant automated tests/lint/type checks are run and pass (or baseline failures are isolated); 4: locale behavior is directly tested or manually verified for Ukrainian, English, default, and switching; 2: commands/results and remaining gaps are accurately reported. Award only applicable checks and explain any unavailable check. |
| Unsupported assumptions | 10 | Start at 10; subtract 2 for each concrete unverified claim or implementation decision concerning architecture, locale behavior, affected scope, keys/resources, dependencies, or verification; subtract 1 for each lower-impact unverified claim. Floor 0. Count distinct assumptions and cite evidence showing they were not verified from repository, task, or supplied context. |
| Maintainability and code quality | 10 | 4: change follows nearby patterns and naming; 3: implementation is clear and minimal; 2: resource/key use avoids duplication and is internally consistent; 1: comments/types/error handling are appropriate to local practice. |
| Execution efficiency | 5 | 2: completes within the common time limit; 1: no avoidable failed verification attempt; 1: no additional corrective iteration after claimed completion; 1: no unnecessary changed file. Use logs, elapsed time, iterations, failures, and file list. |
| **Total** | **100** | Apply any critical-failure cap after summing. |

## Critical-failure conditions and caps

Record critical failures separately from category scoring.

- **Cap at 40:** the defect remains unfixed; tested affected table labels still show Russian in Ukrainian or English; or supported localization is broken.
- **Cap at 50:** the project no longer builds or a relevant mandatory check newly fails because of the change.
- **Cap at 20:** secrets are introduced or unrelated destructive changes are made.

When multiple conditions apply, use the lowest cap. A baseline failure demonstrated unchanged by the run is not itself a run critical failure. Keep the raw subtotal and capped final score visible. A stopped or incomplete run is evaluated from preserved evidence and is subject to applicable caps.

## Evaluator notes template

### Evidence identity

- Neutral result label:
- Evaluator:
- Evaluation date/time:
- Treatment mapping known during initial scoring: yes/no; details:

### Known facts before the experiment

-

### Run observations

-

### Evaluator conclusions

-

### Score record

| Category | Score | Evidence and deductions |
|---|---:|---|
| Functional correctness | /30 | |
| Localization architecture compliance | /20 | |
| Scope discipline | /10 | |
| Verification quality | /15 | |
| Unsupported assumptions | /10 | |
| Maintainability and code quality | /10 | |
| Execution efficiency | /5 | |
| Raw subtotal | /100 | |
| Critical failure(s) and cap | | |
| Final score | /100 | |

### Unsupported-assumption register

| Claim or decision | Source checked | Why unsupported | Deduction |
|---|---|---|---:|
| | | | |

## Tie-breaking rules

If final scores tie, prefer, in order: no critical failure; higher Functional correctness; higher Localization architecture compliance; higher Scope discipline; fewer unsupported assumptions counted; smaller justified diff by changed lines; fewer corrective iterations; shorter elapsed time. If still tied, report a tie rather than inventing a distinction.
