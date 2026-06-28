# Prompt Catalog

Updated: 2026-06-27

This catalog defines the prompt families for LabOS-Sim vortexing evaluation.
Prompt IDs are stable handles for benchmark configs, reports, and future
cross-repo reproduction.

## Standardized output schema (fitting contract)

Every prompt ultimately produces the same four fields, which are the input to the
SDT-IRT models (M1/M2):

```
{ "outcome": "success" | "failure", "failure_modes": [], "confidence": 0.0, "reasoning": "" }
```

- **P1** (closed binary) emits exactly the four core fields; `failure_modes` is
  always `[]` (it does not classify subtypes).
- **P3** (multi-label) emits the four core fields plus the `additional_failures`
  diagnostic (see below).
- **P2** (open detection) does NOT emit the core schema directly. It returns its
  own freeform fields (`error_present`, `observed_errors`, `confidence`,
  `reasoning`), which the **P6** parser converts into the core schema. P6 may
  also return `outcome = "ambiguous"` for rows it cannot map (held out of
  fitting).
- `confidence` is a single scalar, collected as a diagnostic (calibration /
  triage) — it is NOT consumed by the hard-flag M1/M2 fit. It is `null` when the
  model gave none (never fabricated). Per-mode confidence is the enrichment path
  if/when we fit a graded-response variant (M2-G).
- For P3, `failure_modes` is ordered by importance (most important first), which
  preserves the "main issue to fix" signal without a separate field.
- `additional_failures` (emitted by P3 and P6) is a list of
  `{description, evidence}` coupled to the `other_failure` flag: non-empty if and
  only if `other_failure` is in `failure_modes`, otherwise `[]`. It captures
  candidate new taxonomy entries. P6 additionally emits `ambiguous_mentions`
  (parser-specific; P3 forces success/failure so it has no ambiguous bucket).

All prompts share the same correct-vortexing protocol and the same failure-mode
definitions, and all are scoped to the single **target tube** being vortexed
(other tubes in the scene are ignored). The taxonomy is: `cap_open`, `tube_drop`,
`tube_empty`, `vortex_off`, `wrong_orientation`, `wrong_rack`, `rack_flipped`,
`other_failure` (`repeated_steps` was removed).

## Capability levels

- **Easy** — task + success definition + failure-mode taxonomy are all given.
  Can the VLM separate success from failure, and name the failure modes?
  Prompts: P1, P3.
- **Middle** — task + written protocol given, but NOT the failure-mode taxonomy.
  Can the VLM describe what happened and surface the failures in free text?
  Prompt: P2 (parsed by P6).
- **Hard** — realistic deployment: identify the operation in a wet-lab, infer its
  success definition (retrieve the per-operation protocol), then detect failures.
  NOT YET TESTABLE on the current database (one operation, no full protocol).
  Future work; see `capability_levels.md`.

## Active prompts

| Prompt ID | Name | Level | Primary Question | Output | Prompt File | Runner Task |
|---|---|---|---|---|---|---|
| P1 | Closed Binary | Easy | Was this performed correctly? | 4 core fields; `failure_modes` always `[]` | `p1_closed_binary.md` | `binary_success` |
| P2 | Open Detection (protocol-grounded) | Middle | Given the protocol, was there any error? Describe each. | Freeform (`error_present`, `observed_errors`, `confidence`, `reasoning`) → P6 | `p2_open_detection.md` | not wired yet |
| P3 | Multi-label Classification | Easy | Which failure subtype(s) occurred? | 4 core fields + `additional_failures` | `p3_multilabel_classification.md` | replaces `single_choice_multiclass` |
| P6 | Free-text → Subtype Parser | (infra) | Map P2 free text to the core schema. | Core schema + `additional_failures`, `ambiguous_mentions` | `p6_freetext_subtype_parser.md` | parser stage |

### P2 → P6 parsing

P6 takes one P2 output at a time and fills `{{error_present}}`,
`{{observed_errors}}`, `{{confidence}}` (P2's `reasoning` is deliberately NOT
passed, so the parser is not biased by P2's rationale). Behavior:

- If `error_present` is `false`, P6 sets `outcome = "success"`, `failure_modes =
  []`, and empty diagnostics — before any text parsing.
- Otherwise it maps `observed_errors` onto the taxonomy, returning `failure` or
  `ambiguous`.
- `confidence` is carried through verbatim and set to `null` if P2 gave none.

## Removed prompts

These files were deleted (2026-06-26) and substituted by the refined versions:

- `p3_multiclass_classification.md` → replaced by `p3_multilabel_classification.md`
  (single-choice forced mutually-exclusive flags, breaking M2's conditional
  independence and blocking multi-error clips).
- `p4_free_form_description.md` → folded into the middle-level prompt P2.
- `p5_protocol_grounded_counterfactual.md` → folded into P2 (counterfactual field
  dropped as out-of-scope for detection).
- `p5_protocol_grounded_description.md` → merged into P2 (P2 and P5 were the same
  middle-level task; P2 now carries the numbered protocol).

## Legacy prompt files

- `vortexing_binary_success.md`: prior production P1 prompt used by `binary_success`.
- `vortexing_failure_mode_classification.md`: older multi-label P3-style prompt.
- `vortexing_single_choice_multiclass.md`: prior production single-choice P3 prompt.

For new benchmark development, prefer the `p*_*.md` files and update runner task
mappings explicitly when a prompt graduates from catalog entry to active task.
