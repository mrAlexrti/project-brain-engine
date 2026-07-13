# External Tester Guide

1. Install Project Brain Engine with `pip install -e ".[dev]"`.
2. Run `brain app`.
3. Connect a local Git repository and review detected metadata.
4. Complete owner intake without entering secret values.
5. Initialize or select Brain knowledge; validate and explicitly approve only trusted Items.
6. Enter a real task in its original language and evaluator-only Ground Truth.
7. Create an experiment outside the source repository.
8. Run both neutral packages with the same agent configuration. The engine does not invoke an agent.
9. Finish both runs and capture Git evidence.
10. Score both neutral results with written evidence and lock evaluation.
11. Reveal treatment only after lock.
12. Finalize and retain private results or a separately reviewed anonymized export allowed by policy.

Use the same agent product, version, model, reasoning, permissions, network policy, and time limit for both runs. Record prompt counts, questions, iterations, deviations, and explicit zero values. Do not give Ground Truth to either coding run.

For cleanup, follow [Experiment Mode](EXPERIMENT_MODE.md). Never publish raw evidence without owner review.
