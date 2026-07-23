# Evaluation workspace

This directory contains the complete LabOS-Sim evaluation pipeline:

- `config/`: model registry and evaluation defaults.
- `prompts/`: P1–P6 prompt source of truth.
- `scripts/`: data collection, processing, reporting, and workflows.
- `src/labos_benchmark/`: reusable Python evaluation package.
- `design_choices/`: design experiments, collaborator summary, and evidence.
- `docs/`: evaluation architecture and method notes.
- `results/`: final full-run reports.

Evaluation raw runs and regenerable media caches are local under `eval/runs/`
and `eval/.cache/`. Dataset metadata and downloaded videos remain in the
repository-level `data/` directory.
