# VLM design-choice study

This directory keeps the design-development study separate from normal full-run
benchmark outputs while grouping its specification and evidence in one place.

## Layout

- `RESULTS.md`: collaborator-facing summary of the study and selected design.
- `experiment/`: executable runner, design matrix, and fixed sample manifest.
- `artifacts/`: canonical run list, raw provider predictions and call metrics,
  processed detection tables, direct metric reports, and cost summaries.

Run commands and fixed experimental settings are documented in
`experiment/README.md`. Artifact provenance and the output layout are documented
in `artifacts/README.md`. Regenerable local media are cached outside the evidence
tree at `eval/.cache/design_choices/media/` and are not tracked by Git.
