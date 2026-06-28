# Prompt Catalog

Updated: 2026-06-28

This catalog defines the prompt families for LabOS-Sim vortexing evaluation.
Prompt IDs are stable handles for run configs, reports, and reproduction.
Task names follow `{operation}_{prompt_type}` (e.g. `vortex_open_detection_strict`).

## Standardized output schema (fitting contract)

The SDT-IRT models (M1/M2) consume one tidy table whose per-cell rows come from
predictions in this core schema:

```
{ "outcome": "success" | "failure", "failure_modes": [], "confidence": 0.0, "reasoning": "" }
```

Not every prompt emits the core schema directly:

- **P1 / P2** emit it directly (P1: `failure_modes` always `[]`; P2: plus
  `additional_failures`).
- **P3 / P4** are freeform VLM outputs that are *parsed* into the core schema by
  **P5 / P6** respectively. They are NOT fed to `build_detection_table` directly.
- `confidence` is a diagnostic (calibration / triage), not consumed by the
  hard-flag M1/M2 fit; `null` when the model gave none (never fabricated).
- `additional_failures` (P2, P5, P6) is a `{description, evidence}` list coupled to
  the `other_failure` flag (non-empty iff `other_failure ∈ failure_modes`).
  Parsers (P5/P6) additionally emit `ambiguous_mentions` and may return
  `outcome = "ambiguous"` (held out of fitting).

All prompts share the same vortexing protocol and are scoped to the single
**target tube**. The taxonomy is: `cap_open`, `tube_drop`, `tube_empty`,
`vortex_off`, `wrong_orientation`, `wrong_rack`, `rack_flipped`, `other_failure`.

## Capability levels

- **Easy** — task + success definition + failure-mode taxonomy all given.
  Prompts: P1 (binary), P2 (multi-label).
- **Middle** — task + protocol given, taxonomy withheld; two variants:
  - **P3 + P5 (strict / error-aware):** the VLM is told to detect errors and
    lists them succinctly; P5 maps them to the taxonomy.
  - **P4 + P6 (free / error-unaware):** the VLM only *describes* the video (not
    told it is an error-detection test); P6 mines failure modes from the
    description. Tests whether a model notices errors unprompted.
- **Hard** — identify the operation + retrieve its protocol, then detect. Not yet
  testable (one operation, no full protocols); see `../docs/capability_levels.md`.

## Active prompts

| ID | Name | Level | VLM output | Parsed by | Prompt File |
|---|---|---|---|---|---|
| P1 | Closed Binary | Easy | core (`failure_modes`=[]) | — | `p1_closed_binary.md` |
| P2 | Multi-label Classification | Easy | core + `additional_failures` | — | `p2_multilabel_classification.md` |
| P3 | Open Detection — strict (error-aware) | Middle | `outcome`, `observed_errors` (comma string), `confidence` | P5 | `p3_open_detection_strict.md` |
| P4 | Open Detection — free (error-unaware) | Middle | `outcome`, `description`, `confidence` | P6 | `p4_open_detection_free.md` |
| P5 | Strict parser (infra) | — | core schema + diagnostics | — | `p5_open_detection_strict_parser.md` |
| P6 | Free parser (infra) | — | core schema + diagnostics | — | `p6_open_detection_free_parser.md` |

### Parsing (P3→P5, P4→P6)

The runner fills the parser prompt's `{{...}}` placeholders by field name from the
source VLM prediction (`reasoning` excluded):

- **P5** gets `{{outcome}}`, `{{observed_errors}}`, `{{confidence}}`. It honors
  `outcome`: `success` → short-circuit; otherwise map the comma-separated
  `observed_errors` onto the taxonomy.
- **P6** gets `{{outcome}}`, `{{description}}`, `{{confidence}}`. It does NOT
  short-circuit on the VLM `outcome` (the VLM was not error-hunting); it reads the
  `description` and identifies the failure modes it reports.

## History

Earlier iterations (now superseded): a single-choice `p3_multiclass`, a single
merged `p2_open_detection` + `p6_freetext_subtype_parser`, and the free-form
`p4`/`p5` protocol prompts. Legacy production prompts (`vortexing_*.md`) remain in
git history.
