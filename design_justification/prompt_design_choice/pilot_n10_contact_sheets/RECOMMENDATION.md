# Prompt-ablation — recommendation (P1–P6)

**Setup.** 3 models (`qwen3_vl`, `claude_opus_4_8`, `gemini_3_1_pro`) × baseline (B) +
2 reworded variants (V1, V2) per prompt, on 10 clips (3 success + 7 single-mode
failures, one per subtype). Parsers = `gpt_5_5_parser`. Scored from **raw predictions**
(not the detection table, which drops `ambiguous`); `ambiguous` counts as a miss.
Ranking metric: mean balanced accuracy across models (macro-F1 tie-break; prefer B on ties).
720 calls, ~$13.45.

## Winners

| Prompt | Winner | mean balanced acc (B → win) | Why |
|---|---|---|---|
| P1 closed binary | **V1** | 0.484 → **0.587** | "Fail only on a clearly visible violation, else success" stops Opus flagging every clip as failure. |
| P2 multilabel | **V1** (marginal) | 0.460 → **0.524** | "Flag a subtype only when directly/clearly seen" nudges precision; best macro-F1 too. |
| P3 strict | **B (keep)** | **0.587** (variants 0.532) | Rewording did not help; strict VLM already emits clean error lists. |
| P4 free | **V2** (strong) | 0.357 → **0.643** | Per-step structured narration surfaces deviations; cuts Opus `ambiguous` 9→2. |
| P5 strict parser | **V2** (tie) | 0.587 = 0.587 | Outcome identical across all three; V2 wins only on subtype mapping (synonym guide). Keeping B is fine. |
| P6 free parser | **V2** | 0.357 → **0.476** | Synonym guide + "commit over ambiguous" cuts Opus `ambiguous` 9→1. |

## Honest caveats

- **n = 10.** Balanced-accuracy differences ≤ ~0.10 are within sampling noise. Only
  **P4 (Δ+0.29)**, **P1 (Δ+0.10)**, and **P6 (Δ+0.12)** are sizable; P2/P3/P5 are marginal.
- **Effects are driven by `claude_opus_4_8`.** `qwen3_vl` almost always predicts `success`
  (fails to flag) regardless of wording; `gemini_3_1_pro` is success-biased on the free
  tasks. So "optimal wording" mostly = wording that keeps the capable model from
  over-flagging (P1) or collapsing to `ambiguous` (P4/P6).
- **Biggest, most robust win:** the free/error-unaware path (P4→P6). Baseline made Opus
  answer `ambiguous` on 9/10 clips (unusable); the structured-narration + commit variants
  make it produce scorable, mostly-correct judgments.

## Files
- `proposed/` — the winning prompt file for each of P1–P6 (drop-in replacements for `prompts/`).
- `results/report.md`, `results/per_model_metrics.csv` — full numbers.
- `variants/` — all candidates. `HYPOTHESES.md` — what each variant tested.
- This folder is tracked under `design_justification/` (only `runs/.media_cache/` is
  gitignored); the accepted `proposed/` files (P4-V2, P6-V2) are applied in `prompts/`.
