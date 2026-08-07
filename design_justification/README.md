# Design justification

Everything that justifies the benchmark's design choices lives here — the
development experiments that fixed the input pipeline and the prompt wording
before the full evaluation suite is run. Each study keeps its protocol next to
its generated artifacts (only regenerable media caches are gitignored).

| Folder | What it decides | Status |
|---|---|---|
| `design_choices_experiment/` | Media & generation settings: frame budget (128/256/adaptive), per-frame resolution (480/720 px), token budget, camera views. Protocol, sample manifest, and runner. | Complete — selected design recorded in `design_matrix.yaml` (`selected_design`) |
| `eval_design_choices/` | Generated artifacts of the study above: raw predictions/metrics per condition, processed detection tables, accuracy/F1 reports, cost reports. | Complete (8 conditions, Gemini 3.1 Pro, 80 cases) |
| `prompt_design_choice/pilot_n10_contact_sheets/` | Prompt wording: baseline vs two hypothesis-driven rewrites per prompt (P1–P6), 3 models, 10 clips. Variants, raw runs, scoring, recommendation. | Complete — P4-V2/P6-V2 adopted; P1-V1/P2-V1 held pending a larger-sample check (see `design_choices_experiment/prompt_experiments.md`) |
| `prompt_design_choice/screen_n80_independent_frames/` | Confirmation of the held-back prompt variants (P1-V1, P2-V1/V2, P5-V2) on the 80-clip selection under the final independent-frame design, reusing the design-choice baseline run as the B arm. | Set up, not yet run (two-stage: ~$130–175 Flash screen on Arena key, optional ~$137/arm Pro confirmation) |

Fixed factors and cross-references:

- The design-choice study holds prompts constant (P1, P2, P3+P5) while varying
  media; the prompt ablation holds media constant while varying wording.
- `design_choices_experiment/prompt_experiments.md` narrates the prompt history
  (the 2026-07-01 template-copying fix and the 2026-07-08 ablation) and what
  was adopted into `prompts/`.
- Caveat when reading across studies: the prompt ablation ran under the older
  contact-sheet media pipeline; the media study later selected independent
  frames. `prompt_design_choice/screen_n80_independent_frames/` is the confirmation of the held-back P1/P2
  prompt variants under the final media design (built, pending budget).
