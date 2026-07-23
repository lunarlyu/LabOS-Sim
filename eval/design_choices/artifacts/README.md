# Design-choice evaluation artifacts

This directory contains the versioned evidence produced by the sibling
`../experiment/` directory. Both live under the single top-level
`eval/design_choices/` study directory.

## Layout

- `run_lists/selected_80.jsonl`: canonical 80-clip sample set used by every
  condition (10 clips from each of eight outcome/type groups).
- `raw/{run_id}/`: provider predictions, per-call metrics, and resolved run
  configurations. `metrics.jsonl` is the canonical call-level cost record.
- `processed/{run_id}/`: normalized detection tables and descriptive summaries.
- `processed/costs/cost_summary.csv`: retained all-study cost aggregate, including
  historical contact-sheet and independent-frame conditions.
- `results/{run_id}/`: accuracy, balanced accuracy, exact-type, and per-type
  reports.
- `results/{run_prefix}_costs/cost_summary.csv`: condition-level cost totals
  derived from raw metrics.

The media cache is local and gitignored. Call-level `cost_long.csv` and the
deprecated `per_model_outcome.csv` alias are intentionally not stored because
they duplicate canonical raw metrics and `per_model_metrics.csv`, respectively.
Historical `run_config.json` path fields record the launch-time layout and may
predate the current `eval/` directory. They are provenance only; current runners
resolve paths from the repository and write portable repository-relative paths.

To reproduce or extend these artifacts, use `../experiment/run_experiment.py`;
see `../experiment/README.md` for the fixed settings and commands.
