# LabOS-Sim

Benchmark pipeline for evaluating vision-language models on failure detection in
laboratory-automation videos.

## Repository map

- `data/`: project-level datasets. Metadata is tracked; downloaded videos are
  gitignored.
- `eval/`: the complete evaluation workspace: configuration, prompts, scripts,
  reusable source package, design-choice study, documentation, and results.
- `eval/src/labos_benchmark/`: reusable evaluation engine.
- `eval/design_choices/`: design study, collaborator summary, and versioned
  evidence.
- `eval/docs/ARCHITECTURE.md`: detailed evaluation pipeline and data flow.

The design study is isolated from normal full-run outputs. See
`eval/design_choices/README.md` for its internal layout.

## Common workflows

Run a small end-to-end validation:

```bash
eval/scripts/workflows/smoke_test.sh
```

Run the full benchmark suite:

```bash
eval/scripts/workflows/run_full_suite.sh
```

Preview the design-choice conditions without making API calls:

```bash
.venv/bin/python eval/design_choices/experiment/run_experiment.py --dry-run
```
