# Prompt experiments — why and how the prompts were updated

Companion note to the VLM design-choice experiment. The design-choice study
holds the evaluation prompts constant and varies media/generation settings;
this note records the experiments behind the prompt versions themselves. The
full prompt-ablation artifacts (variants, raw predictions, scoring) are now
tracked alongside this note at `design_justification/prompt_design_choice/pilot_n10_contact_sheets/`.

## Timeline of prompt changes

| Date | Change | Where |
|---|---|---|
| 2026-06-27/28 | Restructure: scope all prompts to the single target tube, drop `repeated_steps` from the taxonomy (8 modes), split middle level into strict/error-aware (P3→P5 parser) and free/error-unaware (P4→P6 parser) | commits `def05dd`, `f3a822d` |
| 2026-07-01 | **Template-copying fix + Anthropic schema fix** (details below) | commit `cb24f0b` |
| 2026-07-08 | **Prompt-ablation experiment** (B vs V1 vs V2 per prompt, 3 models, 10 clips); winners for P4 and P6 applied to `prompts/` | this note; `design_justification/prompt_design_choice/pilot_n10_contact_sheets/` |
| 2026-08-07 | **Prompt-ablation v2 screen** (80 clips, independent frames, Gemini 3 Flash): held-back P1-V1/P2-V1 failed to replicate — committed prompts stand; P2-V2 (high-recall) shows consistent but sub-noise gains, pending a Pro confirmation | `design_justification/prompt_design_choice/screen_n80_independent_frames/` |

## 1. The template-copying fix (2026-07-01, `cb24f0b`)

**Problem observed.** All six prompts presented the required output as a
filled-in example JSON (`"confidence": 0.0`, `"reasoning": "Brief visual
evidence."`). Weaker VLMs copied the literals verbatim instead of computing
values — confidence came back a constant `0.0` on every clip, making the
calibration diagnostic useless.

**Fix.** All six output blocks were rewritten as placeholder schemas
(`<number 0.0-1.0: your certainty...>`) with an explicit "replace every value —
do not copy the placeholder text" instruction.

**Second fix in the same commit.** `minimum`/`maximum` were dropped from the
confidence field in the structured-output JSON schema: Anthropic's validator
(via OpenRouter) rejects those keywords on `number` types with a 400, which
failed every `claude_opus_4_8` call. The 0.0–1.0 range is now stated in the
prompt text instead.

**Note for the design-choice runs.** All `design_justification/eval_design_choices` runs used the
post-fix prompts: the P1/P2/P3/P5 files were not modified after `cb24f0b`, the
recorded `run_config.json` schemas carry the min/max-free confidence field, and
predicted confidences vary per clip (0.85–1.0) instead of the pre-fix constant
0.0. So the design-choice conclusions are on the current committed prompt
versions.

## 2. The prompt-ablation experiment (2026-07-08)

**Question.** For each prompt P1–P6, does a reworded variant beat the current
wording ("B")? Each variant encodes one testable hypothesis.

**Setup.**
- Models: `qwen3_vl`, `claude_opus_4_8`, `gemini_3_1_pro`; parsers use `gpt_5_5_parser`.
- Data: 10 clips — 3 success + 7 failures, one per subtype.
- Candidates: B (verbatim post-`cb24f0b` prompt) + V1 + V2 per prompt.
- Scored from raw predictions; parser `ambiguous` counts as a miss (so a parser
  cannot dodge by answering `ambiguous`).
- Metric: mean balanced accuracy across the 3 models (macro-F1 tie-break;
  prefer B on ties — no change without gain).
- 720 calls, ~$13.45.

**Hypotheses per variant.**

| Prompt | V1 | V2 |
|---|---|---|
| P1 closed binary | High-specificity: "fail only on a clearly visible violation, else success" | High-sensitivity: explicit 5-step checklist, fail if ANY step violated |
| P2 multilabel | High-precision: flag a subtype only when directly/clearly seen | High-recall: scan every subtype one-by-one |
| P3 strict | Decisive per-step error listing naming the physical object | Anchor each error phrase to object+defect for cleaner parser mapping |
| P4 free | Detailed description, invite noting deviations (not framed as error hunt) | Structured per-step narration of the 5 protocol steps |
| P5 strict parser | Commit bias: map every error phrase to closest subtype; `ambiguous` only for noise | V1 + explicit synonym→subtype guide |
| P6 free parser | Infer failures from described deviations; commit over `ambiguous` | V1 + explicit synonym→subtype guide |

**Results** (mean balanced accuracy across models; `ambig` = parser `ambiguous` count):

| Prompt | B | V1 | V2 | Winner |
|---|---:|---:|---:|---|
| P1 | 0.484 | **0.587** | 0.508 | V1 |
| P2 | 0.460 | **0.524** | 0.500 | V1 (marginal) |
| P3 | **0.587** | 0.532 | 0.532 | B — keep |
| P4 | 0.357 (ambig 9) | 0.460 (5) | **0.643** (2) | V2 (strong) |
| P5 | 0.587 | 0.587 | **0.587** | tie; V2 wins only on subtype macro-F1 |
| P6 | 0.357 (ambig 9) | 0.429 (3) | **0.476** (1) | V2 |

**Caveats (important).**
- n = 10 clips: balanced-accuracy deltas ≤ ~0.10 are within sampling noise.
  Only P4 (Δ+0.29), P6 (Δ+0.12), and borderline P1 (Δ+0.10) are sizable.
- Effects are driven almost entirely by `claude_opus_4_8`: `qwen3_vl` predicts
  `success` regardless of wording, and `gemini_3_1_pro` is success-biased on
  the free tasks. "Optimal wording" mostly means wording that keeps the capable
  model from over-flagging (P1) or collapsing to `ambiguous` (P4/P6).
- Biggest, most robust win: the free / error-unaware path (P4→P6). The baseline
  wording made Opus answer `ambiguous` on 9/10 clips (unusable); the structured
  per-step narration + commit-over-ambiguous variants make it produce scorable,
  mostly-correct judgments.

## 3. What was adopted

| Prompt | Decision | Rationale |
|---|---|---|
| P4 free | **V2 adopted** into `prompts/p4_open_detection_free.md` | Δ+0.29, fixes the unusable `ambiguous` collapse |
| P6 free parser | **V2 adopted** into `prompts/p6_open_detection_free_parser.md` | Δ+0.12, ambig 9→1 |
| P3 strict | Keep B | B won outright |
| P5 strict parser | Keep B | Outcome-identical tie; not worth churn |
| P1 closed binary | **Not yet adopted** (V1 won, Δ+0.10) | Right at the noise floor for n=10; want confirmation on a larger sample (e.g. the 80-case design-choice selection) before changing an Easy-level prompt mid-benchmark |
| P2 multilabel | **Not yet adopted** (V1 won, Δ+0.06) | Marginal; same reasoning as P1 |

Consequence for the design-choice experiment: its three evaluation prompts
(P1, P2, P3+P5) are all still the `cb24f0b` versions, so nothing in the
adopted P4/P6 update affects those results. If we later adopt P1-V1/P2-V1, the
design-choice baselines would need a re-run on the affected tasks — one more
reason to confirm on a larger sample first.
