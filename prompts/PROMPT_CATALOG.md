# Prompt Catalog

Updated: 2026-06-19

This catalog defines the prompt families for LabOS-Sim vortexing evaluation.
Prompt IDs are stable handles for benchmark configs, reports, and future
cross-repo reproduction.

| Prompt ID | Name | Primary Question | Output Style | Prompt File | Current Runner Task |
|---|---|---|---|---|---|
| P1 | Closed Binary | Was this performed correctly? Yes/No | JSON binary success/failure | `p1_closed_binary.md` | `binary_success` |
| P2 | Open Detection | Was there any error in this video? | JSON error-present plus short description | `p2_open_detection.md` | not wired yet |
| P3 | Multi-class Classification | Which sub-type of error occurred? | JSON single selected class plus confidence/reasoning | `p3_multiclass_classification.md` | `single_choice_multiclass` |
| P4 | Free-form Description | Describe what happened and any deviation from correct execution | JSON free-form event/deviation summary | `p4_free_form_description.md` | not wired yet |
| P5 | Protocol-grounded Counterfactual | Here is the protocol. Did the operator follow it? Identify deviations. | JSON protocol-following verdict plus deviations | `p5_protocol_grounded_counterfactual.md` | not wired yet |

Existing legacy prompt files:

- `vortexing_binary_success.md`: current production P1 prompt used by `binary_success`.
- `vortexing_failure_mode_classification.md`: older multi-label P3-style prompt.
- `vortexing_single_choice_multiclass.md`: current production P3 prompt used by `single_choice_multiclass`.

For new benchmark development, prefer the `p*_*.md` files and update runner
task mappings explicitly when a prompt graduates from catalog entry to active
benchmark task.
