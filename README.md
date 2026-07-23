# LabOS-Sim

Benchmark pipeline for evaluating vision-language models on failure detection in
laboratory-automation videos.

## Repository map

- `src/labos_benchmark/`: reusable dataset, media, provider, and runner logic.
- `scripts/`: command-line entry points, including `scripts/workflows/` for
  end-to-end smoke and full-suite runs.
- `config/` and `prompts/`: model registries, defaults, schemas, and prompt text.
- `data/`: tracked metadata catalogs plus locally downloaded, gitignored videos.
- `runs/` and `results/`: normal benchmark outputs.
- `design_choices/`: self-contained design study, with experiment definitions
  under `experiment/` and versioned evidence under `artifacts/`.
- `docs/ARCHITECTURE.md`: detailed pipeline structure and data flow.

The design study is isolated from normal full-run outputs. See
`design_choices/README.md` for its internal layout.

## Common workflows

Run a small end-to-end validation:

```bash
scripts/workflows/smoke_test.sh
```

Run the full benchmark suite:

```bash
scripts/workflows/run_full_suite.sh
```

Preview the design-choice conditions without making API calls:

```bash
.venv/bin/python design_choices/experiment/run_experiment.py --dry-run
```
