# 3dkidShop Localization A/B Experiment

**Status:** completed

## Purpose and hypothesis

This controlled experiment compares two fresh AI coding-agent runs on the same real defect in `mrAlexrti/3dkidShop`. It tests the hypothesis that an agent supplied with a Project Brain Context Package produces a more correct, architecture-compliant, and focused implementation than the same agent given only the task and repository.

The storefront supports Ukrainian and English localization, but some table column labels remain Russian after a locale switch. The implementation must discover and reuse the existing localization mechanism and must not introduce an unrelated redesign. Exact paths, components, keys, libraries, and implementation details are deliberately not specified.

One experiment cannot establish general effectiveness. It can provide evidence for this repository, defect, baseline, model, and protocol.

## Files

- `TASK.md`: the single canonical prompt used verbatim in both runs.
- `EXPERIMENT_PROTOCOL.md`: preparation, isolation, execution, evidence, and evaluation procedure.
- `EVALUATION_RUBRIC.md`: the 100-point scoring system.
- `RUN_A_NO_BRAIN.md`: fillable record for the repository-and-task-only run.
- `RUN_B_WITH_BRAIN.md`: fillable record for the Context Package run.
- `RESULTS.md`: unfilled comparison and conclusion template.

## Run distinction

Run A receives only the canonical prompt and repository. Run B receives those same inputs plus a Project Brain-generated Context Package as separate context. That package is the only intended independent variable. Before either run, freeze and record one exact baseline commit from the historically used `redesign-3dkid-v2` branch, then create equivalent isolated workspaces from that commit. Keep sessions and outputs isolated until both runs finish.

## Execution checklist

- [ ] Record all required environment and baseline metadata.
- [ ] Freeze one exact target commit and confirm both workspaces use it.
- [ ] Record the canonical prompt text and hash.
- [ ] Establish equivalent clean `workspace-a` and `workspace-b` environments.
- [ ] Confirm identical model, reasoning effort, permissions, time budget, and network policy.
- [ ] Start fresh, isolated agent sessions; run A without a Context Package.
- [ ] Generate, archive, hash, and separately supply the Context Package to run B.
- [ ] Archive complete evidence before inspecting the other run's output.
- [ ] Assign neutral result labels and evaluate behavior and diffs before reasoning or treatment reveal where practical.
- [ ] Record deviations, scores, limitations, and the unblinded conclusion without claiming general proof.

