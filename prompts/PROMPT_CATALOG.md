# Prompt Catalog

Updated: 2026-06-26

This catalog defines the prompt families for LabOS-Sim vortexing evaluation.
Prompt IDs are stable handles for benchmark configs, reports, and future
cross-repo reproduction.

## Standardized output schema (fitting contract)

Every prompt ultimately produces the same four fields, which are the input to the
SDT-IRT models (M1/M2):

```
{ "outcome": "success" | "failure", "failure_modes": [], "confidence": 0.0, "reasoning": "" }
```

- Closed-form prompts (P1, P3) emit this schema directly.
- Freeform prompts (P2, P5) emit natural language and are converted into this
  schema by the P6 parser (which may also return `outcome = "ambiguous"` plus
  diagnostic buckets).
- `confidence` is a single scalar for now. A per-mode confidence is the natural
  enrichment if/when we fit a graded-response variant (M2-G).
- For P3, `failure_modes` is ordered by importance (most important first), which
  preserves the "main issue to fix" signal without a separate field.

## Capability levels

- **Easy** — task + success definition + failure-mode taxonomy are all given.
  Can the VLM separate success from failure, and name the failure modes?
  Prompts: P1, P3.
- **Middle** — task + written protocol given, but NOT the failure-mode taxonomy.
  Can the VLM describe what happened and surface the failures in free text?
  Prompts: P2, P5 (both parsed by P6).
- **Hard** — realistic deployment: identify the operation in a wet-lab, infer its
  success definition (retrieve the per-operation protocol), then detect failures.
  NOT YET TESTABLE on the current database (one operation, no full protocol).
  Future work; see `capability_levels.md`.

## Active prompts

| Prompt ID | Name | Level | Primary Question | Output | Prompt File | Runner Task |
|---|---|---|---|---|---|---|
| P1 | Closed Binary | Easy | Was this performed correctly? | Schema (outcome only; `failure_modes` always []) | `p1_closed_binary.md` | `binary_success` |
| P2 | Open Detection | Middle | Was there any error? Describe each. | Freeform → P6 | `p2_open_detection.md` | not wired yet |
| P3 | Multi-label Classification | Easy | Which failure subtype(s) occurred? | Schema (multi-label `failure_modes`) | `p3_multilabel_classification.md` | replaces `single_choice_multiclass` |
| P5 | Protocol-grounded Description | Middle | Describe; did the operator follow the protocol? List deviations. | Freeform → P6 | `p5_protocol_grounded_description.md` | not wired yet |
| P6 | Free-text → Subtype Parser | (infra) | Map free text to the standardized schema. | Schema + diagnostics | `p6_freetext_subtype_parser.md` | parser stage |

## Removed prompts

These files were deleted (2026-06-26) and substituted by the refined versions:

- `p3_multiclass_classification.md` → replaced by `p3_multilabel_classification.md`
  (single-choice forced mutually-exclusive flags, breaking M2's conditional
  independence and blocking multi-error clips).
- `p4_free_form_description.md` → merged into `p5_protocol_grounded_description.md`.
- `p5_protocol_grounded_counterfactual.md` → merged into
  `p5_protocol_grounded_description.md` (counterfactual field dropped as
  out-of-scope for detection).

## Legacy prompt files

- `vortexing_binary_success.md`: prior production P1 prompt used by `binary_success`.
- `vortexing_failure_mode_classification.md`: older multi-label P3-style prompt.
- `vortexing_single_choice_multiclass.md`: prior production single-choice P3 prompt.

For new benchmark development, prefer the `p*_*.md` files and update runner task
mappings explicitly when a prompt graduates from catalog entry to active task.
