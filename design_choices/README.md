# VLM design-choice study

This directory keeps the design-development study separate from normal full-run
benchmark outputs while grouping its specification and evidence in one place.

## Layout

- `experiment/`: executable runner, design matrix, fixed sample manifest, and
  collaborator-facing results brief.
- `artifacts/`: canonical run list, raw provider predictions and call metrics,
  processed detection tables, direct metric reports, and cost summaries.

Run commands and fixed experimental settings are documented in
`experiment/README.md`. Artifact provenance and the output layout are documented
in `artifacts/README.md`.
