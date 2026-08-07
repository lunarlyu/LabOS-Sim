# Prompt ablation v2 — 80-clip confirmation under the final media design

**Status: stage-1 screen COMPLETE (2026-08-07, gemini_3_flash via Arena,
$87.40 actual). Verdict: keep the committed prompts; P2-V2 is the only
variant that earned a stage-2 look. See Results below.**

The July 8 prompt ablation (`../pilot_n10_contact_sheets/`) ran on 10 clips with the
contact-sheet media pipeline and three models. Two of its winners (P1-V1,
P2-V1) were held back from adoption because the deltas were near the n=10
noise floor. The design-choice study then replaced contact sheets with
independent frames — and the committed run data shows that change flipped
P2's failure mode from "collapse onto one type" (tube_empty = 57% of flags)
to "under-flagging" (24/70 failures called success, concentrated on
motion-dependent subtypes). So the held-back winners need re-testing under
the final design before adoption.

## Design

- **Sample:** the design-choice 80-clip selection
  (`../design_choices_experiment/selected_samples_10_per_type.csv`) — 10
  successes + 10 per failure subtype. Same clips as every design-choice
  condition.
- **Media/generation:** pinned to `selected_design` from
  `../design_choices_experiment/design_matrix.yaml`: independent frames,
  128/view, front+left+right, 720 px, JPEG q=10, 2048 tokens, temperature 0,
  5 retries, Gemini 3.1 Pro via OpenRouter.
- **B arm is free:** the completed design-choice baseline run
  (`../eval_design_choices/raw/gemini31pro_multiframe_design_02_baseline_f128_views3_tok2048_res720/`)
  used the current committed prompts under exactly this condition, so it IS
  the baseline arm for P1, P2, and P3. Only variant arms are run.
- **Variant files:** read from `../pilot_n10_contact_sheets/variants/` (single source
  of truth; hypotheses in `../pilot_n10_contact_sheets/HYPOTHESES.md`).

## Two-stage design: cheap screening, targeted confirmation

Running everything on the anchor model (Gemini 3.1 Pro) costs ~$137/arm
(~$420 for three variant arms). To keep cost down, the runner defaults to a
**screening stage on Gemini 3 Flash** (same model family, ~$35/arm):

- **Stage 1 — screen (default):** all arms incl. fresh B arms on
  `gemini_3_flash`, ~$130–175 total. Self-consistent: B and variants share
  the same model, provider, and route, so there is no cross-key confound.
- **Stage 2 — confirm (optional):** only the variant(s) that beat B in stage
  1, on `gemini_3_1_pro` (~$137/arm), compared against the committed
  design-choice baseline run as the B arm.

Staying inside the Gemini family maximizes the chance that wording effects
transfer from Flash to Pro; the v1 lesson that prompt effects are
model-dependent is why stage 2 exists at all.

## Arms

| Arm | Prompt | Hypothesis |
|---|---|---|
| `p1_b`, `p2_b` | committed `prompts/` baselines | screening-stage B arms (skipped on `gemini_3_1_pro`, whose B is the committed baseline run) |
| `p1_v1` | P1 high-specificity ("fail only on a clearly visible violation") | v1 winner (Δ+0.10 at n=10); may cut over-flagging |
| `p2_v1` | P2 high-precision ("flag only when directly seen") | v1 winner (Δ+0.06, marginal) |
| `p2_v2` | P2 high-recall ("scan every subtype one-by-one") | lost at n=10 under contact sheets, but the under-flagging regime under independent frames favors recall wording |
| `p5_v2` | P5 synonym-guide parser re-scoring the committed baseline P3 output | better subtype macro-F1 at zero outcome change in v1 (~$1, parser-only) |

Cost basis: the design-choice cost reports show ~$130–140 per 80-clip
prompt-task for Gemini 3.1 Pro (~36M input tokens); Flash estimates scale by
its OpenRouter price ratio with the same ~1.9x observed-vs-naive calibration.

Not included (deliberately): Opus/Qwen arms — 384 images/call exceeds
Anthropic per-request image limits and Qwen is not needed for a
Gemini-anchored benchmark; P4/P6 free-path arms — the adopted P4-V2/P6-V2
have no independent-frame B arm to compare against (would need 2 extra VLM
arms; revisit if the free path enters the headline suite).

## Providers / billing

`--provider arena` (default) bills Carrie's Arena key
(`https://api.preview.arena.ai/v1`, OpenAI-compatible; key from
`ARENA_API_KEY`, falling back to `ANTHROPIC_AUTH_TOKEN`). Verified to accept
vision calls for both Gemini models. `--provider openrouter` bills Luna's
OpenRouter key from `_env.json`.

Route caveat: the stage-1 screen is provider-self-consistent under either
key. For stage 2, the committed B arm ran through OpenRouter, so running
variant arms on Arena adds a provider-route confound on top of the known
temperature-0 non-determinism; prefer `--provider openrouter` for stage 2,
or add `--arm p1_b --arm p2_b` to rebuild the B arm on Arena (+2 x ~$137).
The P5 parser always uses OpenRouter (`gpt_5_5_parser`).

## Run

Preview (no API calls):

```bash
.venv/bin/python design_justification/prompt_design_choice/screen_n80_independent_frames/run_experiment.py --dry-run
```

Stage 1 validation on 3 clips (~$7):

```bash
.venv/bin/python design_justification/prompt_design_choice/screen_n80_independent_frames/run_experiment.py --limit 3
```

Stage 1 full screen (~$130–175, Arena billing):

```bash
.venv/bin/python design_justification/prompt_design_choice/screen_n80_independent_frames/run_experiment.py --concurrency 2
```

Stage 2 confirmation of a winning variant (example):

```bash
.venv/bin/python design_justification/prompt_design_choice/screen_n80_independent_frames/run_experiment.py \
  --model gemini_3_1_pro --provider openrouter --arm p2_v2 --concurrency 2
```

One arm only: `--arm p2_v2` (repeatable). Reruns retry only failed samples.
If the design-choice media cache exists locally, it is symlinked and reused
(identical transcode settings), skipping ffmpeg work.

## Results — stage-1 screen (gemini_3_flash, 80 clips, 2026-08-07)

| Arm | Exact-acc / balanced-acc | Macro-F1 (fail) | Failure recall | Verdict |
|---|---:|---:|---:|---|
| P1-B | bal 0.514 (fail recall 0.029) | — | 0.029 | **keep** |
| P1-V1 | bal 0.500 (fail recall 0.000) | — | 0.000 | reject — high-specificity wording zeroes detection in the under-flagging regime |
| P2-B | exact 0.175 | 0.090 | 0.071 | **keep (default)** |
| P2-V1 | exact 0.163 | 0.092 | 0.071 | reject — n=10 win did not replicate |
| P2-V2 | exact 0.213 | 0.122 | 0.114 | **stage-2 candidate** — consistent gains on every metric incl. vortex_off recall 0→0.4, but Δexact (+3 clips) is within the n=80 noise floor |
| P5-V2 | exact 0.1875 | — | — | reject — exactly ties the committed P5-B (0.1875) on Pro's baseline P3 output |

Headline: **both held-back n=10 winners (P1-V1, P2-V1) failed to replicate**,
vindicating the decision not to adopt them. The committed prompts stand. The
open question is P2-V2 on the anchor model: one `--model gemini_3_1_pro
--provider openrouter --arm p2_v2` run (~$137) against the committed baseline
settles it.

Context numbers: Flash is far weaker than Pro here (P2 exact 0.175 vs 0.30;
P1 failure recall 0.029 — it calls 68/70 failures "success"), so wording
effects on Flash may understate or overstate Pro's. Actual arm cost ≈ $17.4
(not the ~$35 estimated — Flash image tokens bill at list token rate).

## Outputs and scoring

Per arm `promptabl2_{model}_{arm}`: raw predictions/metrics under `runs/raw/`,
detection tables under `runs/processed/`, accuracy/F1 reports under
`runs/results/`, cost under `runs/results/promptabl2_costs/`. Compare each
arm's `runs/results/promptabl2_{arm}/` against the committed B-arm reports in
`../eval_design_choices/results/gemini31pro_multiframe_design_02_baseline_f128_views3_tok2048_res720/`.

Adoption rule (same as v1): prefer B on ties; require the variant to beat B
on balanced accuracy with the subtype macro-F1 as tie-break. Note the
non-determinism floor measured in the design study (temperature 0 through
OpenRouter is not deterministic; P2 primary-type self-agreement was 15/30 on
identical inputs) — treat differences within that floor as ties.
