# Controlled Experiment Mode

The protocol compares two neutral results from the same task and exact Git baseline. Exactly one run package contains the frozen Context Package. Treatment and run order are randomized independently.

```bash
brain experiment init --repository REPO --output OUTSIDE_REPO --task-file TASK.md --ground-truth-file GROUND_TRUTH.md --brain-path BRAIN
brain experiment status OUTSIDE_REPO
brain experiment context OUTSIDE_REPO
brain experiment start OUTSIDE_REPO --result result-1
brain experiment finish OUTSIDE_REPO --result result-1 --final-report report.txt
brain experiment capture OUTSIDE_REPO --result result-1
brain experiment finalize OUTSIDE_REPO
```

Creation requires a clean source repository and refuses existing output or output inside the repository. It creates `workspace-1`, `workspace-2`, and `workspace-context` as detached worktrees at the frozen SHA. New experiment Brain knowledge exists only in `workspace-context`. A baseline already containing `.brain` is rejected by default; explicit acknowledgement classifies the experiment as a contaminated pilot and prevents it from being reported as a clean A/B result.

The treatment map is `evidence/private/treatment-map.yaml`. Normal status excludes mapping and run order. Ground Truth is evaluator-only and never copied into a run package. The neutral evaluator package excludes the private treatment map and Context assignment.

Finalization requires two captured and validated evidence sets, matching task and Context hashes, Brain isolation, a treatment-neutral evaluator package, locked evaluation, and post-lock reveal. The SHA-256 manifest covers only controlled experiment artifacts, never workspaces, source trees, or dependencies, and excludes itself deterministically. The revealed final report includes category scores and evidence, caps, assumptions, deviations, comparison classification, and treatment result.

## Worktree cleanup

After preserving evidence, inspect `git worktree list`, then run:

```bash
git -C /path/to/source worktree remove /path/to/experiment/workspace-1
git -C /path/to/source worktree remove /path/to/experiment/workspace-2
git -C /path/to/source worktree remove /path/to/experiment/workspace-context
git -C /path/to/source worktree prune
```

Do not delete worktree directories manually while Git still registers them.
