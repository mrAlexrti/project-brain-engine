# Experiment Protocol

## 1. Purpose

Produce reproducible comparative evidence about Project Brain Context Package access on one real `3dkidShop` localization defect while holding the agent and execution conditions constant.

## 2. Hypothesis

An AI coding agent supplied with a Project Brain Context Package will produce a more correct, architecture-compliant, and focused implementation than the same agent receiving only the task and repository.

This is a scoped test, not proof of general effectiveness.

## 3. Independent variable

Access to the archived Project Brain-generated Context Package. Run A has no access to it. Run B receives it as separate context. No other deliberate difference is permitted.

## 4. Controlled variables

Both runs must use the same exact baseline commit, canonical task text, model, reasoning effort, Codex/tool version, tool permissions and approval behavior, maximum execution time, network-access policy, dependency state, available commands, and equivalent fresh workspace configuration. The planned initial configuration is `gpt-5.6-sol` with reasoning effort `medium`; record the actual configuration used.

## 5. Required environment information

Record before execution:

| Field | Value |
|---|---|
| Target repository URL | TODO |
| Exact baseline commit SHA | TODO |
| Baseline branch | TODO |
| Operating system/version | TODO |
| Node.js version | TODO |
| Package manager/version | TODO |
| Codex version | TODO |
| Model | TODO |
| Reasoning effort | TODO |
| Maximum execution time | TODO |
| Tool permissions/approval policy | TODO |
| Network-access policy | TODO |
| Canonical prompt hash and algorithm (or exact text) | TODO |
| Date/time and time zone | TODO |
| Dependency installation command | TODO |
| Baseline build/test commands and results | TODO |

## 6. Baseline preparation

1. Obtain the target repository from its recorded URL. The historically used development branch is `redesign-3dkid-v2`; do not assume its current tip is the baseline.
2. Select and record one full commit SHA before either run. Verify that both workspaces resolve `HEAD` to that SHA.
3. Record the exact canonical prompt text and a cryptographic hash using a named algorithm.
4. Record all environment information above, including actual tool/model versions rather than planned values.
5. Install dependencies using the same recorded command and lockfile behavior in both workspaces.
6. Run and record the available baseline build/test checks before agent execution. A failing baseline is not silently attributed to either run.
7. Preserve a read-only baseline snapshot or otherwise retain enough evidence to reproduce it.

## 7. Workspace isolation

Create two independent clean workspaces, neutrally named `workspace-a` and `workspace-b`, from the exact baseline SHA. Do not use treatment-revealing branch or directory names in evaluator-facing evidence. Confirm equivalent dependency state, configuration, permissions, approval behavior, time budget, and network policy.

Use a fresh Codex session for each run. Do not resume any prior Project Brain or `3dkidShop` session. Do not copy/paste between runs, view the first run's diff before completing the second, or expose either run's transcript, reasoning, commands, or output to the other. Each run must begin with a clean working tree and no untracked evidence from the other run.

## 8. Run A procedure

1. Confirm the clean workspace, baseline SHA, environment, clock, and time limit.
2. Start a fresh agent session with the controlled model, effort, permissions, approval behavior, and network policy.
3. Supply only the exact canonical `TASK.md` prompt and repository access. Do not supply Project Brain output or Brain-derived hints.
4. Let the agent work until it reports completion or a stopping condition occurs.
5. Capture all evidence listed below before inspecting Run B output.

## 9. Run B procedure

1. Bootstrap target-project Brain knowledge as a separate prerequisite outside this specification task, then generate a Context Package with the recorded Project Brain Engine revision and exact `brain context` command and request answers.
2. Archive the package in its exact supplied format, hash it, and record its execution status, missing Questions, and Critical, Required, and Supporting Item IDs. Do not modify it in response to Run A.
3. Confirm the clean workspace, baseline SHA, environment, clock, and time limit.
4. Start a fresh agent session under controls identical to Run A.
5. Supply the exact canonical prompt, repository access, and the archived Context Package as separate context. Supply no manually added implementation hint absent from that package.
6. Let the agent work until it reports completion or a stopping condition occurs.
7. Capture all evidence listed below.

## 10. Evidence collection

Archive for each run:

- complete agent final report;
- full Git diff and a separate changed-file list;
- commands executed, with order and outcomes;
- build, test, lint, and manual-verification results, including failures;
- start/finish times and elapsed time;
- permission-prompt count and clarification-question count;
- unsupported assumptions identified later by the evaluator;
- number and description of additional corrective iterations;
- final `git status` and working-tree state;
- protocol deviations and stopping condition, if any.

Also archive the exact Run B Context Package, its hash, generation command, request answers, and Project Brain version/commit. Store artifacts under neutral result labels with an integrity manifest where practical.

## 11. Evaluation procedure

1. Freeze and archive both outputs, assign neutral result labels, and withhold the treatment mapping from the evaluator where practical.
2. Evaluate functional behavior and verification evidence, then inspect and score diffs using `EVALUATION_RUBRIC.md`, without reading agent reasoning first.
3. Record concrete unsupported assumptions and critical failures. Apply score caps exactly as specified.
4. Resolve ties using the rubric rules.
5. Reveal which result used Brain only after initial scoring; inspect agent reasoning afterward and record any score changes with justification.

Perfect evaluator blinding is not guaranteed because package effects may be inferable from artifacts. Record who knew the mapping and when.

## 12. Contamination controls

- Use fresh sessions with no resumed context or shared agent memory.
- Deny both agents access to the other run's workspace and archived outputs.
- Do not transfer prompts, messages, diffs, discoveries, corrections, or evaluator feedback between runs.
- Complete both runs before viewing the first run's diff in preparation for the second.
- Generate Run B context independently of Run A and archive it before Run B begins.
- Give Run A no Project Brain package, summary, or Brain-derived hint.
- Give Run B no manual implementation hint absent from its archived package.
- Use identical canonical prompt bytes and record/hash them.
- Keep permissions, approvals, time limit, network policy, tooling, baseline, and dependency installation equivalent.
- Keep evaluator-facing labels neutral until initial scoring is locked.
- Log any accidental exposure as a protocol deviation; do not silently repair contamination.

## 13. Stopping conditions

Stop a run when the identical maximum execution time expires, the agent declares completion, an unrecoverable environment failure prevents meaningful work, permissions required by the controlled policy are unavailable, or continuing risks destructive/unrelated changes. Preserve partial evidence and classify the stop. Do not grant one run extra time or corrective interaction; an equivalent rule must be applied to both.

## 14. Limitations

This is one defect, repository, baseline, model configuration, stochastic pair of sessions, and generated Context Package. Repository drift, evaluator judgment, imperfect blinding, manual verification limits, package quality, tool nondeterminism, and order effects can influence results. A score difference does not isolate which package Item caused it and does not prove broad causal effectiveness.

## 15. Repetition strategy

Repeat paired runs across multiple fresh session pairs using the same frozen baseline and protocol, counterbalancing execution order while keeping result labels neutral. Record random seeds if the vendor exposes them. Then repeat on additional defects, repositories, model families, reasoning settings, and independently reviewed Context Packages. Report individual results and distributions; do not pool protocol deviations as clean repetitions.
