# LabOS-Sim Baseline Tracking

Updated: 2026-06-16

## Full Binary Benchmark Overview, 1080px/30fps

Updated: 2026-06-14

This overview compares the full 257-sample binary success/failure benchmarks using the common `1080px/30fps` all-view video profile. All costs are total OpenRouter spend for the full run.

| Model family | Requested model | Resolved model version | Run directory | Parse errors | Strict accuracy | Success accuracy | Failure accuracy | TP | TN | FP | FN | Cost |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MiniMax | `minimax/minimax-m3` | `minimax/minimax-m3-20260531` | `runs/binary_full_minimax_1080p30fps_001` | 1 | 189/257 = 73.5% | 0/61 = 0.0% | 189/196 = 96.4% | 0 | 189 | 6 | 61 | $0.972969 |
| Gemini Flash | `google/gemini-3.5-flash` | `google/gemini-3.5-flash-20260519` | `runs/binary_full_gemini_flash_1080p30fps_001` | 2 | 140/257 = 54.5% | 50/61 = 82.0% | 90/196 = 45.9% | 50 | 90 | 105 | 10 | $2.933551 |
| Gemini Pro | `google/gemini-3.1-pro-preview-20260219` | `google/gemini-3.1-pro-preview-20260219` | `runs/binary_full_gemini_pro_1080p30fps_001` | 0 | 150/257 = 58.4% | 48/61 = 78.7% | 102/196 = 52.0% | 48 | 102 | 94 | 13 | $4.002542 |
| Qwen | `qwen/qwen3.6-plus` | `qwen/qwen3.6-plus-04-02` | `runs/binary_full_qwen_1080p30fps_001` | 0 | 139/257 = 54.1% | 57/61 = 93.4% | 82/196 = 41.8% | 57 | 82 | 114 | 4 | $2.265505 |

Interpretation: MiniMax is the strongest failure detector and the cheapest full run, but it classified every success as failure. Qwen is the strongest success recognizer, but over-accepts many failures. Gemini Pro is currently the most balanced of the full `1080px/30fps` runs, with no parse errors and the best combined success/failure tradeoff among Gemini Flash, Gemini Pro, and Qwen.

## Post-Retry Consolidation, Full 1080px/30fps Benchmarks

Updated: 2026-06-16

Scope: active full `1080px/30fps` binary and multiclass benchmarks. Failed API calls and parse-error rows were retried up to 2 times. Successful retry rows are consolidated into the metrics below; original raw-run sections remain in this file for auditability.

Confidence requirement update: future parsed predictions now require a numeric `confidence` field in `[0, 1]`. Responses that parse as JSON but omit valid confidence are treated as parse errors by the runner.

Retry artifact: `runs/retry_consolidation_full_1080p30fps.json`

Canonical retry procedure: after completing the active full `1080px/30fps`
binary and multiclass runs, execute `python scripts/retry_failed_full_benchmarks.py`.
The script retries failed API rows and parse-error rows up to 2 times, writes
generated retry configs to `runs/retry_configs/`, records retry run directories
under `runs/`, and emits the consolidated metrics artifact above. Use
consolidated metrics and total cost with retries for headline reporting; keep
the base run metrics below for auditability.

Binary results after retry consolidation:

| Model | Base run | Initial failed rows | Recovered | Unresolved | Accuracy | TP | TN | FP | FN | Base cost | Retry cost | Total cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MiniMax | `runs/binary_full_minimax_1080p30fps_001` | 1 | 1 | 0 | 190/257 = 73.9% | 0 | 190 | 6 | 61 | $0.972969 | $0.001416 | $0.974385 |
| Gemini Flash | `runs/binary_full_gemini_flash_1080p30fps_001` | 2 | 2 | 0 | 141/257 = 54.9% | 50 | 91 | 105 | 11 | $2.933551 | $0.055599 | $2.989150 |
| Gemini Pro | `runs/binary_full_gemini_pro_1080p30fps_001` | 0 | 0 | 0 | 150/257 = 58.4% | 48 | 102 | 94 | 13 | $4.002542 | $0.000000 | $4.002542 |
| Qwen | `runs/binary_full_qwen_1080p30fps_001` | 0 | 0 | 0 | 139/257 = 54.1% | 57 | 82 | 114 | 4 | $2.265505 | $0.000000 | $2.265505 |

Multiclass results after retry consolidation:

| Model | Base run | Initial failed rows | Recovered | Unresolved | Outcome accuracy | Exact target accuracy | Expected label included | Base cost | Retry cost | Total cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemini Flash | `runs/multiclass_full_gemini_flash_1080p30fps_001` | 1 | 1 | 0 | 143/257 = 55.6% | 93/257 = 36.2% | 98/257 = 38.1% | $3.313478 | $0.013353 | $3.326831 |
| Gemini Pro | `runs/multiclass_full_gemini_pro_1080p30fps_001` | 10 | 10 | 0 | 161/257 = 62.6% | 87/257 = 33.9% | 97/257 = 37.7% | $4.248082 | $0.196296 | $4.444378 |
| MiniMax | `runs/multiclass_full_minimax_1080p30fps_001` | 3 | 3 | 0 | 175/257 = 68.1% | 36/257 = 14.0% | 52/257 = 20.2% | $0.970001 | $0.012039 | $0.982039 |
| Qwen | `runs/multiclass_full_qwen_1080p30fps_001` | 0 | 0 | 0 | 127/257 = 49.4% | 69/257 = 26.8% | 87/257 = 33.9% | $2.279913 | $0.000000 | $2.279913 |

Retry read: all active full-suite failed rows recovered within the two-retry budget, so there are no unresolved failures to carry forward. MiniMax remains cheapest, Gemini Pro remains the most balanced binary model, and multiclass exact failure-mode labeling remains the hardest task for every model.

## AUROC, Full 1080px/30fps Benchmarks

Updated: 2026-06-16

AUROC artifact: `runs/auroc_full_1080p30fps.json`

Confidence retry artifact: `runs/confidence_retry_full_1080p30fps.json`

Method: AUROC is success-positive. Because model outputs report confidence in
the predicted class, the ranking score is `confidence` when the model predicts
success and `1 - confidence` when the model predicts failure. This is a ranking
score, not a calibrated probability estimate. Rows without numeric confidence
are excluded from AUROC here; future runs treat missing or invalid confidence as
parse errors.

Supplemental confidence retry: completed rows that were missing valid
confidence were retried up to 2 times. This recovered 13/16 rows for an
additional $0.297281 OpenRouter spend. Gemini Flash still has 3 unresolved
no-confidence rows after the retry budget.

| Model | Task | Scored rows | Positives | Negatives | Missing confidence | Success-positive AUROC |
|---|---|---:|---:|---:|---:|---:|
| MiniMax | Binary | 257 | 61 | 196 | 0 | 0.543 |
| Gemini Flash | Binary | 256 | 61 | 195 | 1 | 0.649 |
| Gemini Pro | Binary | 257 | 61 | 196 | 0 | 0.653 |
| Qwen | Binary | 257 | 61 | 196 | 0 | 0.687 |
| Gemini Flash | Multiclass outcome | 255 | 59 | 196 | 2 | 0.650 |
| Gemini Pro | Multiclass outcome | 257 | 61 | 196 | 0 | 0.664 |
| MiniMax | Multiclass outcome | 257 | 61 | 196 | 0 | 0.544 |
| Qwen | Multiclass outcome | 257 | 61 | 196 | 0 | 0.658 |

Unresolved no-confidence rows after supplemental retry:

- Gemini Flash binary: `real_human_carrie_01_cap_open_fail_cap_loose_07`
- Gemini Flash multiclass: `real_human_carrie_00_success_success_01_clean`
- Gemini Flash multiclass: `real_human_carrie_00_success_success_vortex_on_02`

## Full Comparison Report Bundle

Updated: 2026-06-18

Report artifact: `reports/full_1080p30fps/summary.md`

Generated with `python scripts/report_full_benchmark_comparison.py`. The report
uses failed-row retry consolidation, merges successful confidence-retry rows,
and reports total OpenRouter spend including retry attempts.

Generated tables:

- `reports/full_1080p30fps/binary_model_summary.csv`
- `reports/full_1080p30fps/multiclass_model_summary.csv`
- `reports/full_1080p30fps/binary_per_category_accuracy.csv`
- `reports/full_1080p30fps/multiclass_per_category_metrics.csv`

Generated charts:

- `reports/full_1080p30fps/charts/binary_overall_metrics.svg`
- `reports/full_1080p30fps/charts/multiclass_overall_metrics.svg`
- `reports/full_1080p30fps/charts/binary_per_category_accuracy.svg`
- `reports/full_1080p30fps/charts/multiclass_per_category_expected_label.svg`
- `reports/full_1080p30fps/charts/cost_by_model.svg`

## Baseline: Binary Success Detection, 10 Samples

Purpose: first reproducible binary benchmark over 3 clean successes and 7 failure cases using OpenRouter video calls. The prompt asks whether the vortexing task succeeded under the current success criteria, and the model must return parseable JSON only.

### Fixed Configuration

| Setting | Value |
|---|---|
| Task | `binary_success` only |
| Dataset metadata | `metadata/real_human_samples.json` |
| Sample panel | 3 `clean` successes + 7 failures, one from each major failure folder |
| Video views | all available camera views per sample |
| Videos per sample | all videos, normally 5 |
| Media profile | `canonical_clip_720px_15fps` |
| Preprocess | transcode to max width 720px, 15fps, CRF 28, preset `veryfast` |
| Temperature | 0 |
| Structured output enforcement | disabled for video compatibility; local JSON parsing still required |

### Model Configurations

| Model family | Config | Requested model | Resolved model(s) | Reasoning setting | Max completion tokens |
|---|---|---|---|---|---:|
| Gemini | `configs/benchmarks/binary_10_gemini_720p15fps.json` | `google/gemini-3.1-pro-preview-20260219` | `google/gemini-3.1-pro-preview-20260219` | `{"exclude":true}` | 2000 |
| MiniMax | `configs/benchmarks/binary_10_minimax_720p15fps.json` | `minimax/minimax-m3` | `minimax/minimax-m3-20260531` | `{"effort":"none","exclude":true}` | 700 |

### Sample Panel

| # | Sample ID | Expected | Label | Videos | Path |
|---:|---|---|---|---:|---|
| 1 | `real_human_carrie_00_success_success_01_clean` | success | clean | 5 | `video_Carrie/00_success/success_01_clean` |
| 2 | `real_human_carrie_00_success_success_02_clean` | success | clean | 5 | `video_Carrie/00_success/success_02_clean` |
| 3 | `real_human_carrie_00_success_success_03_clean` | success | clean | 5 | `video_Carrie/00_success/success_03_clean` |
| 4 | `real_human_carrie_01_cap_open_fail_cap_loose_01` | failure | cap_open | 5 | `video_Carrie/01_cap_open/fail_cap_loose_01` |
| 5 | `real_human_carrie_02_tube_drop_fail_tube_drop_01` | failure | tube_drop | 5 | `video_Carrie/02_tube_drop/fail_tube_drop_01` |
| 6 | `real_human_carrie_03_tube_empty_fail_tube_empty_01` | failure | tube_empty | 5 | `video_Carrie/03_tube_empty/fail_tube_empty_01` |
| 7 | `real_human_carrie_04_vortex_off_fail_vortex_off_01` | failure | vortex_off | 5 | `video_Carrie/04_vortex_off/fail_vortex_off_01` |
| 8 | `real_human_carrie_05_wrong_orientation_fail_wrong_orientation_01` | failure | wrong_orientation | 5 | `video_Carrie/05_wrong_orientation/fail_wrong_orientation_01` |
| 9 | `real_human_carrie_06_wrong_rack_fail_wrong_rack_01` | failure | wrong_rack | 5 | `video_Carrie/06_wrong_rack/fail_wrong_rack_01` |
| 10 | `real_human_carrie_07_rack_flipped_fail_rack_flipped_01` | failure | rack_flipped | 5 | `video_Carrie/07_rack_flipped/fail_rack_flipped_01` |

### Aggregate Results

| Model | Run directory | Completed | Parse errors | Accuracy | TP | TN | FP | FN | OpenRouter spend | Prompt tokens | Completion tokens | Reasoning tokens | Reported video tokens |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemini | `runs/binary10_gemini_720p15fps_001` | 10/10 | 0 | 50.0% | 3 | 2 | 5 | 0 | $0.136752 | 32436 | 5990 | 5411 | 27000 |
| MiniMax | `runs/binary10_minimax_720p15fps_001` | 10/10 | 0 | 90.0% | 2 | 7 | 0 | 1 | $0.055389 | 183670 | 545 | 0 | 0 |

Notes: Gemini still consumes internal reasoning tokens even with `reasoning.exclude=true`; the reasoning text is not returned. MiniMax resolved to the dated endpoint shown above and reported `reasoning_tokens=0`. MiniMax does not report explicit `video_tokens` here; the video input appears in the much larger prompt-token count/cost instead.

### Gemini Per-Sample Results

| Sample | Expected | Prediction | Correct | Confidence | Observed failure | Cost |
|---|---|---|---:|---:|---|---:|
| `real_human_carrie_00_success_success_01_clean` | success | success | yes | 0.95 |  | $0.020156 |
| `real_human_carrie_00_success_success_02_clean` | success | success | yes | 0.9 |  | $0.017804 |
| `real_human_carrie_00_success_success_03_clean` | success | success | yes | 1.0 |  | $0.012832 |
| `real_human_carrie_01_cap_open_fail_cap_loose_01` | failure | success | no | 1.0 |  | $0.013996 |
| `real_human_carrie_02_tube_drop_fail_tube_drop_01` | failure | failure | yes | 1.0 | The tube was placed into a clear bin instead of a tube holder or test tube rack. | $0.015776 |
| `real_human_carrie_03_tube_empty_fail_tube_empty_01` | failure | success | no | 0.95 |  | $0.010616 |
| `real_human_carrie_04_vortex_off_fail_vortex_off_01` | failure | success | no | 0.85 |  | $0.012548 |
| `real_human_carrie_05_wrong_orientation_fail_wrong_orientation_01` | failure | success | no | 0.9 |  | $0.012464 |
| `real_human_carrie_06_wrong_rack_fail_wrong_rack_01` | failure | success | no | 0.9 |  | $0.012044 |
| `real_human_carrie_07_rack_flipped_fail_rack_flipped_01` | failure | failure | yes | 0.7 | No interaction with tube or vortexer. | $0.008516 |

### MiniMax Per-Sample Results

| Sample | Expected | Prediction | Correct | Confidence | Observed failure | Cost |
|---|---|---|---:|---:|---|---:|
| `real_human_carrie_00_success_success_01_clean` | success | success | yes | 0.85 |  | $0.008492 |
| `real_human_carrie_00_success_success_02_clean` | success | success | yes | 0.95 |  | $0.006133 |
| `real_human_carrie_00_success_success_03_clean` | success | failure | no | 0.88 | Vortexer does not turn on; no visible liquid agitation or movement. | $0.005550 |
| `real_human_carrie_01_cap_open_fail_cap_loose_01` | failure | failure | yes | 0.92 | No visible vortexer activation or liquid agitation | $0.006725 |
| `real_human_carrie_02_tube_drop_fail_tube_drop_01` | failure | failure | yes | 0.9 | No visible vortexer operation or liquid movement; the tube is merely touched to the vortexer briefly without spinning. | $0.006152 |
| `real_human_carrie_03_tube_empty_fail_tube_empty_01` | failure | failure | yes | 0.9 | No visible vortexing action; vortexer was not turned on. | $0.003684 |
| `real_human_carrie_04_vortex_off_fail_vortex_off_01` | failure | failure | yes | 0.9 | The human places the tube on the vortexer but does not turn it on, so the vortexer never runs. | $0.004376 |
| `real_human_carrie_05_wrong_orientation_fail_wrong_orientation_01` | failure | failure | yes | 0.9 | vortexer did not run | $0.006722 |
| `real_human_carrie_06_wrong_rack_fail_wrong_rack_01` | failure | failure | yes | 0.75 | No visible vortexer activation; tube was placed and removed without the vortexer running. | $0.004961 |
| `real_human_carrie_07_rack_flipped_fail_rack_flipped_01` | failure | failure | yes | 0.95 | No vortexing action occurs; human knocks over a tube rack. | $0.002595 |

### Initial Read

MiniMax produced both the strongest and cheapest first binary baseline on this 10-sample panel: 90.0% accuracy for $0.055389 total OpenRouter spend.

## Gemini Smoke Media Variants

Updated: 2026-06-12

Purpose: test whether Gemini can run with higher frame rate and/or higher resolution than the canonical 720px/15fps setting. The source videos for these two smoke samples are 1920x1200 at 30fps, so the 1080px and 1920px variants increase actual input resolution.

Fixed settings: `binary_success` only, `google/gemini-3.1-pro-preview-20260219`, all 5 camera views per sample, temperature 0, `reasoning.exclude=true`, and `max_completion_tokens=2000`.

Smoke samples:

| Sample ID | Expected | Path |
|---|---|---|
| `real_human_carrie_00_success_success_01_clean` | success | `video_Carrie/00_success/success_01_clean` |
| `real_human_carrie_02_tube_drop_fail_tube_drop_01` | failure | `video_Carrie/02_tube_drop/fail_tube_drop_01` |

| Variant | Config | Run directory | Completed | Accuracy | OpenRouter spend | Prompt tokens | Completion tokens | Reasoning tokens | Reported video tokens | Transcoded media size |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 720px/30fps | `configs/benchmarks/gemini_smoke_binary_720p30fps.json` | `runs/gemini_smoke_binary_720p30fps_001` | 2/2 | 50.0% | $0.046276 | 8288 | 2475 | 2358 | 7200 | 1.81 MB |
| 1080px/15fps | `configs/benchmarks/gemini_smoke_binary_1080p15fps.json` | `runs/gemini_smoke_binary_1080p15fps_001` | 2/2 | 50.0% | $0.035392 | 8288 | 1568 | 1451 | 7200 | 3.20 MB |
| 1080px/30fps | `configs/benchmarks/gemini_smoke_binary_1080p30fps.json` | `runs/gemini_smoke_binary_1080p30fps_001` | 2/2 | 100.0% | $0.035200 | 8288 | 1552 | 1435 | 7200 | 3.46 MB |
| 1920px/30fps | `configs/benchmarks/gemini_smoke_binary_1920p30fps.json` | `runs/gemini_smoke_binary_1920p30fps_001` | 2/2 | 100.0% | $0.042400 | 8288 | 2152 | 2030 | 7200 | 12.42 MB |

Per-sample read: 720px/30fps and 1080px/15fps both misclassified the clean success as a failure due to an alleged rack/holder issue. The 1080px/30fps and 1920px/30fps variants classified both smoke samples correctly. Gemini reported the same number of video tokens across these variants; cost differences mainly came from completion/reasoning token variation rather than the larger transcoded media bytes.

## MiniMax Smoke Media Variants

Updated: 2026-06-12

Purpose: mirror the Gemini media-variant smoke test for MiniMax using the same two samples, same binary prompt, same all-view input, and the same fps/resolution variants.

Fixed settings: `binary_success` only, requested model `minimax/minimax-m3`, resolved model `minimax/minimax-m3-20260531`, all 5 camera views per sample, temperature 0, `reasoning.effort=none`, `reasoning.exclude=true`, and `max_completion_tokens=700`.

| Variant | Config | Run directory | Completed | Accuracy | OpenRouter spend | Prompt tokens | Completion tokens | Reasoning tokens | Reported video tokens | Transcoded media size |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 720px/30fps | `configs/benchmarks/minimax_smoke_binary_720p30fps.json` | `runs/minimax_smoke_binary_720p30fps_001` | 2/2 | 100.0% | $0.014628 | 48554 | 97 | 0 | 0 | 1.81 MB |
| 1080px/15fps | `configs/benchmarks/minimax_smoke_binary_1080p15fps.json` | `runs/minimax_smoke_binary_1080p15fps_001` | 2/2 | 50.0% | $0.014667 | 48554 | 130 | 0 | 0 | 3.20 MB |
| 1080px/30fps | `configs/benchmarks/minimax_smoke_binary_1080p30fps.json` | `runs/minimax_smoke_binary_1080p30fps_001` | 2/2 | 50.0% | $0.014660 | 48554 | 124 | 0 | 0 | 3.46 MB |
| 1920px/30fps | `configs/benchmarks/minimax_smoke_binary_1920p30fps.json` | `runs/minimax_smoke_binary_1920p30fps_001` | 2/2 | 50.0% | $0.013776 | 45674 | 107 | 0 | 0 | 12.42 MB |

Per-sample read: MiniMax classified the tube-drop failure correctly in all four variants. It only classified the clean success correctly at 720px/30fps; the higher-resolution variants marked the clean success as failure because they did not observe visible vortexer/liquid agitation. MiniMax reported no reasoning tokens and no explicit video tokens; OpenRouter appears to account for the video payload in prompt tokens for this model family.

## Baseline: Binary Success Detection, 10 Samples, 1920px/30fps

Updated: 2026-06-12

Purpose: rerun the same 10-sample binary panel using the selected high-fidelity profile: all available camera views, max width 1920px, 30fps, CRF 28, preset `veryfast`.

| Model | Config | Run directory | Completed | Accuracy | TP | TN | FP | FN | OpenRouter spend | Prompt tokens | Completion tokens | Reasoning tokens | Reported video tokens | Transcoded media size |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemini | `configs/benchmarks/binary_10_gemini_1920p30fps.json` | `runs/binary10_gemini_1920p30fps_001` | 10/10 | 70.0% | 3 | 4 | 3 | 0 | $0.156356 | 32434 | 7624 | 7049 | 27000 | 51.38 MB |
| MiniMax | `configs/benchmarks/binary_10_minimax_1920p30fps.json` | `runs/binary10_minimax_1920p30fps_001` | 10/10 | 70.0% | 1 | 6 | 1 | 2 | $0.052228 | 172870 | 534 | 0 | 0 | 51.38 MB |

Per-sample read: Gemini classified all 3 clean successes correctly, but over-accepted 3 failures: `vortex_off`, `wrong_orientation`, and `wrong_rack`. MiniMax was cheaper and caught 6 of 7 failures, but missed 2 of the 3 clean successes and over-accepted `wrong_orientation`.

## Candidate Model Suite Notes

Updated: 2026-06-12

OpenRouter catalog check: the original families are still a reasonable benchmark suite for comparison against a world model, but exact model IDs should be pinned instead of using mutable aliases.

| Family | Status | Recommended benchmark role |
|---|---|---|
| Gemini Pro | Keep, but pin exact ID after smoke test | Flagship commercial video baseline. Avoid `~google/gemini-pro-latest` for final runs because it can move under us. |
| Gemini Flash | Keep if budget/latency matters | Useful fast/cheap Gemini-family comparator. `google/gemini-3.5-flash` is video-capable in OpenRouter's catalog. |
| MiniMax | Keep | Strong cost/performance video-native comparator; current resolved model in runs is `minimax/minimax-m3-20260531`. |
| StepFun | Keep | `stepfun/step-3.7-flash` is listed as text+image+video input and gives another non-Google/MiniMax video-native family. |
| Perceptron | Keep as a domain-relevant probe | `perceptron/perceptron-mk1` is explicitly text+image+video input and is worth testing because it is positioned around video/embodied reasoning. |
| Qwen | Keep, but update candidate | `qwen/qwen3.6-plus` is available and video-capable; `qwen/qwen3.7-plus` is newer in the catalog but currently appears as text+image only, so `qwen/qwen3.6-plus` is the safer video benchmark target unless a video-capable 3.7 model appears. |

Suggested initial world-model comparison set: Gemini Pro exact pinned model, MiniMax M3, StepFun Step 3.7 Flash, Perceptron Mk1, Qwen3.6 Plus, and one cheaper Gemini Flash variant. This balances flagship general VLM, low-cost commercial VLM, specialist/embodied-video candidate, and Chinese multimodal families without making the first matrix too large.

## Autoscreen: Additional Models, 10 Samples, 1920px/30fps

Updated: 2026-06-12

Purpose: run the same binary prompt and same high-fidelity video setup against Gemini Flash, StepFun, Perceptron, and Qwen. The fixed setup is all available camera views, all videos per sample, max width 1920px, 30fps, CRF 28, preset `veryfast`, temperature 0, and local JSON parsing of model output.

| Model | Config | Run directory | Requested / resolved model | Reasoning setting | Completed | Failed | Parse errors | Accuracy over planned | TP | TN | FP | FN | OpenRouter spend | Prompt tokens | Completion tokens | Reasoning tokens | Reported video tokens |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemini Flash | `configs/benchmarks/binary_10_gemini_flash_1920p30fps.json` | `runs/binary10_gemini_flash_1920p30fps_001` | `google/gemini-3.5-flash` / `google/gemini-3.5-flash-20260519` | `{"exclude":true}` | 10/10 | 0 | 0 | 40.0% | 1 | 3 | 4 | 2 | $0.117966 | 32426 | 7703 | 7098 | 27000 |
| StepFun | `configs/benchmarks/binary_10_stepfun_1920p30fps.json` | `runs/binary10_stepfun_1920p30fps_002` | `stepfun/step-3.7-flash` / `stepfun/step-3.7-flash-20260528` | `{"exclude":true}` | 1/10 | 9 | 1 | 0.0% | 0 | 0 | 0 | 0 | $0.000000 | 0 | 0 | 0 | 0 |
| Perceptron | `configs/benchmarks/binary_10_perceptron_1920p30fps.json` | `runs/binary10_perceptron_1920p30fps_001` | `perceptron/perceptron-mk1` / `perceptron/perceptron-mk1-20260512` | `{"effort":"none","exclude":true}` | 7/10 | 3 | 7 | 0.0% | 0 | 0 | 0 | 0 | $0.000000 | 0 | 0 | 0 | 0 |
| Qwen | `configs/benchmarks/binary_10_qwen_1920p30fps.json` | `runs/binary10_qwen_1920p30fps_001` | `qwen/qwen3.6-plus` / `qwen/qwen3.6-plus-04-02` | `{"effort":"none","exclude":true}` | 10/10 | 0 | 0 | 50.0% | 2 | 3 | 4 | 1 | $0.095574 | 290270 | 634 | 0 | 0 |

Provider notes:

- Gemini Flash completed all calls, but like Gemini Pro it still consumed internal reasoning tokens even though reasoning text was excluded. It over-accepted 4 failures and missed 2 clean successes.
- StepFun rejected the initial no-thinking run (`reasoning.effort=none`) because reasoning is mandatory for the endpoint. The rerun with only `reasoning.exclude=true` still failed at the selected setup because the provider reported: `The amount of videos you provided exceeds the model's limitation.`
- Perceptron could not produce usable JSON at the selected setup. Three calls exceeded the 32768-token context window; the other seven returned provider error payloads or empty model output, so they were recorded as parse errors.
- Qwen completed all calls with no reasoning tokens reported, but over-accepted 4 failures and missed 1 clean success.

Autoscreen read: at the selected all-view 1920px/30fps setup, the viable models so far are Gemini Pro, MiniMax, Gemini Flash, and Qwen. StepFun is removed from the active benchmark suite because its provider rejects the all-view video-count setup. Perceptron likely needs fewer views or a lower-fidelity media profile to fit its context window.

## Follow-Up: StepFun and Perceptron, 10 Samples, 720px/15fps

Updated: 2026-06-12

Purpose: retry StepFun and Perceptron with smaller clips while keeping the same 10-sample binary panel, same prompt, all available camera views, and all videos per sample.

| Model | Config | Run directory | Requested / resolved model | Reasoning setting | Completed | Failed | Parse errors | Accuracy over planned | TP | TN | FP | FN | OpenRouter spend | Prompt tokens | Completion tokens | Reasoning tokens | Reported video tokens | Transcoded media size |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| StepFun | `configs/benchmarks/binary_10_stepfun_720p15fps.json` | `runs/binary10_stepfun_720p15fps_001` | `stepfun/step-3.7-flash` / unavailable from failed calls | `{"exclude":true}` | 0/10 | 10 | 0 | 0.0% | 0 | 0 | 0 | 0 | $0.000000 | 0 | 0 | 0 | 0 | 6.98 MB |
| Perceptron | `configs/benchmarks/binary_10_perceptron_720p15fps.json` | `runs/binary10_perceptron_720p15fps_001` | `perceptron/perceptron-mk1` / `perceptron/perceptron-mk1-20260512` | `{"effort":"none","exclude":true}` | 10/10 | 0 | 0 | 50.0% | 2 | 3 | 4 | 1 | $0.021696 | 138600 | 604 | 0 | 0 | 6.98 MB |

Follow-up read:

- StepFun still failed on every sample with the provider error: `The amount of videos you provided exceeds the model's limitation.` Because this persisted at 720px/15fps, the blocker appears to be number of videos per request rather than media resolution or byte size. StepFun should be rerun with fewer camera views or one video per call plus an aggregation strategy.
- Perceptron became viable at 720px/15fps: all 10 requests completed, all outputs parsed, and no reasoning tokens were reported. It reached 50.0% accuracy, over-accepting 4 failures and missing 1 clean success.

## Perceptron Smoke Retest, 1920px/30fps

Updated: 2026-06-12

Purpose: retest Perceptron on the two canonical smoke samples with the high-fidelity all-view setup after deciding to remove StepFun from the active suite.

| Model | Config | Run directory | Completed | Failed | Parse errors | Usable accuracy | OpenRouter spend | Result |
|---|---|---|---:|---:|---:|---:|---:|---|
| Perceptron | `configs/benchmarks/perceptron_smoke_binary_1920p30fps.json` | `runs/perceptron_smoke_binary_1920p30fps_001` | 2/2 | 0 | 2 | 0.0% | $0.000000 | Both responses were provider error payloads with empty model output. |

Smoke samples:

| Sample ID | Expected | Status | Provider response |
|---|---|---|---|
| `real_human_carrie_00_success_success_01_clean` | success | parse error | `Provider returned error`, code 400 |
| `real_human_carrie_02_tube_drop_fail_tube_drop_01` | failure | parse error | `Provider returned error`, code 400 |

Retest read: Perceptron is not usable with all 5 camera videos at 1920px/30fps, even on the 2-sample smoke test. Perceptron is removed from the active 1920px/30fps benchmark suite for now. It remains viable only at the smaller 720px/15fps all-view profile unless we reduce camera views or split videos into separate calls.

## Full Set: MiniMax Binary, 1920px/30fps

Updated: 2026-06-12

Purpose: run the binary success/failure benchmark on the full metadata set using the selected high-fidelity profile. Perceptron and StepFun are excluded from the active high-resolution suite; this run uses MiniMax only.

Configuration:

| Setting | Value |
|---|---|
| Config | `configs/benchmarks/binary_full_minimax_1920p30fps.json` |
| Run directory | `runs/binary_full_minimax_1920p30fps_001` |
| Model | requested `minimax/minimax-m3`; resolved mostly as `minimax/minimax-m3-20260531` |
| Task | `binary_success` |
| Samples | 257 total: 61 success, 196 failure |
| Media | all available camera views, all videos per sample, max width 1920px, 30fps, CRF 28 |
| Reasoning request | `{"effort":"none","exclude":true}` |

Aggregate results:

| Metric | Value |
|---|---:|
| Planned calls | 257 |
| API failed calls | 0 |
| Completed rows | 257 |
| Strict parseable rows | 121 |
| Parse errors | 136 |
| Strict accuracy over planned | 74/257 = 28.8% |
| Accuracy over parseable rows only | 74/121 = 61.2% |
| TP | 9 |
| TN | 65 |
| FP | 21 |
| FN | 26 |
| OpenRouter spend | $0.791020 |
| Prompt tokens | 3,978,722 |
| Completion tokens | 63,845 |
| Reasoning tokens reported | 55,819 |
| Reported video tokens | 0 |
| Transcoded media size | 1,330.95 MB |

Outcome breakdown:

| Ground truth outcome | Correct | Total | Accuracy |
|---|---:|---:|---:|
| Success | 9 | 61 | 14.8% |
| Failure | 65 | 196 | 33.2% |

Task breakdown:

| Task family | Correct | Total | Accuracy |
|---|---:|---:|---:|
| `basic_vortexing` | 48 | 157 | 30.6% |
| `closing_cap` | 17 | 61 | 27.9% |
| `vortexing_after_turning_on_vortexer` | 8 | 36 | 22.2% |
| `ambiguous_multiple_task` | 1 | 3 | 33.3% |

Label breakdown:

| Label | Correct | Total | Accuracy |
|---|---:|---:|---:|
| `cap_open` | 14 | 48 | 29.2% |
| `rack_flipped` | 17 | 33 | 51.5% |
| `repeated_steps` | 1 | 1 | 100.0% |
| `tube_drop` | 12 | 32 | 37.5% |
| `tube_empty` | 4 | 13 | 30.8% |
| `vortex_off` | 6 | 27 | 22.2% |
| `wrong_orientation` | 5 | 12 | 41.7% |
| `wrong_rack` | 6 | 32 | 18.8% |
| `success:cap_close` | 3 | 13 | 23.1% |
| `success:clean` | 0 | 15 | 0.0% |
| `success:correct_rack` | 4 | 14 | 28.6% |
| `success:tube_nonempty` | 0 | 8 | 0.0% |
| `success:vortex_on` | 2 | 11 | 18.2% |

Parse-error breakdown:

| Kind | Count |
|---|---:|
| Duplicate/extra JSON data | 74 |
| `null` output | 50 |
| Empty output | 10 |
| Other JSON parse issue | 2 |

Parse errors by ground truth: 26 success samples and 110 failure samples.

Full-set read: MiniMax is API-viable on the full all-view 1920px/30fps dataset, but output-format reliability collapsed at scale. Strict scoring gives 28.8% over all planned samples, while the parseable subset scores 61.2%. The run was configured with `reasoning.effort=none`, but 90 responses still reported reasoning tokens and many of those hit `finish_reason=length`; treat this as observed MiniMax/OpenRouter behavior at this high-fidelity full-set scale rather than a clean no-thinking run.

## Smoke: MiniMax 20 Samples, 1080px/30fps

Updated: 2026-06-13

Purpose: test whether a lower high-fidelity profile can preserve full API/parse reliability while avoiding the full-set 1920px/30fps MiniMax output-format failures. The 20-sample panel contains 6 successes and 14 failures: 5 clean successes, 1 correct-rack success, and 2 examples from each major failure family.

| Variant | Config | Run directory | Completed | Failed | Parse errors | Finish reasons | Reasoning tokens | Strict accuracy | TP | TN | FP | FN | OpenRouter spend | Prompt tokens | Completion tokens | Media size |
|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `effort=none` | `configs/benchmarks/binary_20_minimax_1080p30fps.json` | `runs/binary20_minimax_1080p30fps_001` | 20/20 | 0 | 0 | `stop:20` | 0 | 70.0% | 0 | 14 | 0 | 6 | $0.078226 | 263655 | 1080 | 29.75 MB |
| `max_tokens=1` | `configs/benchmarks/binary_20_minimax_1080p30fps_reasoning_max1.json` | `runs/binary20_minimax_1080p30fps_reasoning_max1_001` | 20/20 | 0 | 12 | `stop:9`, `length:11` | 11462 | 15.0% | 2 | 1 | 5 | 0 | $0.058035 | 337200 | 11438 | 29.75 MB |

Read: `1080px/30fps` with `reasoning.effort=none` achieved the desired technical success rate: 20/20 calls completed, 20/20 parsed, no reasoning tokens were reported, and every response stopped normally. The remaining problem is semantic, not API reliability: MiniMax classified all 6 success samples as failures, usually because it claimed no visible vortexer/liquid agitation or no rack return. The `reasoning.max_tokens=1` config option made things worse, causing length stops, reasoning tokens, and parse errors. For MiniMax, the best current reliability profile is `1080px/30fps` with `effort=none`.

## Full Set Rerun: MiniMax Binary, 1080px/30fps

Updated: 2026-06-13

Purpose: rerun the full MiniMax binary benchmark using the reliable `1080px/30fps` profile found in the 20-sample smoke test. The full benchmark summary includes final OpenRouter cost.

Configuration:

| Setting | Value |
|---|---|
| Config | `configs/benchmarks/binary_full_minimax_1080p30fps.json` |
| Run directory | `runs/binary_full_minimax_1080p30fps_001` |
| Model | requested `minimax/minimax-m3`; resolved `minimax/minimax-m3-20260531` |
| Task | `binary_success` |
| Samples | 257 total: 61 success, 196 failure |
| Media | all available camera views, all videos per sample, max width 1080px, 30fps, CRF 28 |
| Reasoning request | `{"effort":"none","exclude":true}` |
| Final OpenRouter cost | $0.972969 |

Aggregate results:

| Metric | Value |
|---|---:|
| Planned calls | 257 |
| API failed calls | 0 |
| Completed rows | 257 |
| Strict parseable rows | 256 |
| Parse errors | 1 |
| Strict accuracy over planned | 189/257 = 73.5% |
| TP | 0 |
| TN | 189 |
| FP | 6 |
| FN | 61 |
| OpenRouter spend | $0.972969 |
| Prompt tokens | 3,310,309 |
| Completion tokens | 14,274 |
| Reasoning tokens reported | 712 |
| Reported video tokens | 0 |
| Finish reasons | `stop:256`, `length:1` |
| Transcoded media size | 379.73 MB |

Outcome breakdown:

| Ground truth outcome | Correct | Total | Accuracy |
|---|---:|---:|---:|
| Success | 0 | 61 | 0.0% |
| Failure | 189 | 196 | 96.4% |

Task breakdown:

| Task family | Correct | Total | Accuracy |
|---|---:|---:|---:|
| `basic_vortexing` | 117 | 157 | 74.5% |
| `closing_cap` | 44 | 61 | 72.1% |
| `vortexing_after_turning_on_vortexer` | 25 | 36 | 69.4% |
| `ambiguous_multiple_task` | 3 | 3 | 100.0% |

Label breakdown:

| Label | Correct | Total | Accuracy |
|---|---:|---:|---:|
| `cap_open` | 44 | 48 | 91.7% |
| `rack_flipped` | 32 | 33 | 97.0% |
| `repeated_steps` | 1 | 1 | 100.0% |
| `tube_drop` | 32 | 32 | 100.0% |
| `tube_empty` | 13 | 13 | 100.0% |
| `vortex_off` | 27 | 27 | 100.0% |
| `wrong_orientation` | 12 | 12 | 100.0% |
| `wrong_rack` | 30 | 32 | 93.8% |
| `success:cap_close` | 0 | 13 | 0.0% |
| `success:clean` | 0 | 15 | 0.0% |
| `success:correct_rack` | 0 | 14 | 0.0% |
| `success:tube_nonempty` | 0 | 8 | 0.0% |
| `success:vortex_on` | 0 | 11 | 0.0% |

Full-rerun read: `1080px/30fps` fixed the output reliability problem from the full `1920px/30fps` run: parse errors dropped from 136 to 1, and length stops dropped to 1. The final cost of this full benchmark was $0.972969. The semantic failure mode is now clear: MiniMax classified every success sample as failure, usually because it could not see visible vortexer/liquid agitation or a rack return. This profile is technically reliable but biased toward failure detection.

## Smoke and Full Set: Gemini Flash Binary, 1080px/30fps

Updated: 2026-06-13

Purpose: gate Gemini Flash on the same 20-sample `1080px/30fps` smoke panel used for MiniMax, then run the full 257-sample benchmark if no parsing errors occur.

Smoke gate:

| Metric | Value |
|---|---:|
| Config | `configs/benchmarks/binary_20_gemini_flash_1080p30fps.json` |
| Run directory | `runs/binary20_gemini_flash_1080p30fps_001` |
| Completed | 20/20 |
| API failed calls | 0 |
| Parse errors | 0 |
| Finish reasons | `stop:20` |
| Strict accuracy | 10/20 = 50.0% |
| TP | 2 |
| TN | 8 |
| FP | 6 |
| FN | 4 |
| OpenRouter spend | $0.252492 |
| Reasoning tokens reported | 16,309 |

Because the smoke gate had 0 parse errors, the full benchmark was run.

Full benchmark:

| Metric | Value |
|---|---:|
| Config | `configs/benchmarks/binary_full_gemini_flash_1080p30fps.json` |
| Run directory | `runs/binary_full_gemini_flash_1080p30fps_001` |
| Model | requested `google/gemini-3.5-flash`; resolved mostly `google/gemini-3.5-flash-20260519` |
| Samples | 257 total: 61 success, 196 failure |
| Media | all available camera views, all videos per sample, max width 1080px, 30fps, CRF 28 |
| Reasoning request | `{"exclude":true}` |
| Final OpenRouter cost | $2.933551 |

Aggregate results:

| Metric | Value |
|---|---:|
| Planned calls | 257 |
| API failed calls | 0 |
| Completed rows | 257 |
| Strict parseable rows | 255 |
| Parse errors | 2 |
| Strict accuracy over planned | 140/257 = 54.5% |
| TP | 50 |
| TN | 90 |
| FP | 105 |
| FN | 10 |
| OpenRouter spend | $2.933551 |
| Prompt tokens | 790,679 |
| Completion tokens | 194,723 |
| Reasoning tokens reported | 180,000 |
| Reported video tokens | 651,900 |
| Finish reasons | `stop:257` |
| Transcoded media size | 379.73 MB |

Outcome breakdown:

| Ground truth outcome | Correct | Total | Accuracy |
|---|---:|---:|---:|
| Success | 50 | 61 | 82.0% |
| Failure | 90 | 196 | 45.9% |

Task breakdown:

| Task family | Correct | Total | Accuracy |
|---|---:|---:|---:|
| `basic_vortexing` | 96 | 157 | 61.1% |
| `closing_cap` | 33 | 61 | 54.1% |
| `vortexing_after_turning_on_vortexer` | 11 | 36 | 30.6% |
| `ambiguous_multiple_task` | 0 | 3 | 0.0% |

Label breakdown:

| Label | Correct | Total | Accuracy |
|---|---:|---:|---:|
| `cap_open` | 21 | 48 | 43.8% |
| `rack_flipped` | 24 | 33 | 72.7% |
| `repeated_steps` | 0 | 1 | 0.0% |
| `tube_drop` | 29 | 32 | 90.6% |
| `tube_empty` | 5 | 13 | 38.5% |
| `vortex_off` | 3 | 27 | 11.1% |
| `wrong_orientation` | 2 | 12 | 16.7% |
| `wrong_rack` | 6 | 32 | 18.8% |
| `success:cap_close` | 12 | 13 | 92.3% |
| `success:clean` | 11 | 15 | 73.3% |
| `success:correct_rack` | 12 | 14 | 85.7% |
| `success:tube_nonempty` | 7 | 8 | 87.5% |
| `success:vortex_on` | 8 | 11 | 72.7% |

Parse-error notes:

- `real_human_carrie_00_success_success_vortex_on_10`: provider returned a 502 error payload, causing empty output.
- `real_human_carrie_01_cap_open_fail_cap_loose_31`: model returned non-JSON text despite `finish_reason=stop`.

Full-run read: Gemini Flash at `1080px/30fps` is mostly parse-reliable but not perfectly parse-clean at full scale: the 20-sample smoke had 0 parse errors, while the full run had 2 parse errors. It is much better than MiniMax at recognizing success samples, but much worse at recognizing many failure modes, especially `vortex_off`, `wrong_orientation`, and `wrong_rack`. The final cost of this full benchmark was $2.933551.

## Smoke and Full Set: Gemini Pro and Qwen Binary, 1080px/30fps

Updated: 2026-06-14

Purpose: run the binary success/failure benchmark for Gemini Pro and Qwen using the same `1080px/30fps` profile. Each model first ran the 20-sample smoke gate; because both smoke gates had 0 parse errors, each model then ran the full 257-sample benchmark.

Smoke gates:

| Model | Config | Run directory | Completed | Parse errors | Strict accuracy | TP | TN | FP | FN | OpenRouter spend | Reasoning tokens | Finish reasons |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Gemini Pro | `configs/benchmarks/binary_20_gemini_pro_1080p30fps.json` | `runs/binary20_gemini_pro_1080p30fps_001` | 20/20 | 0 | 55.0% | 5 | 6 | 8 | 1 | $0.329656 | 15,773 | `stop:20` |
| Qwen | `configs/benchmarks/binary_20_qwen_1080p30fps.json` | `runs/binary20_qwen_1080p30fps_001` | 20/20 | 0 | 50.0% | 5 | 5 | 9 | 1 | $0.181310 | 0 | `stop:20` |

Full benchmark summary:

| Model | Config | Run directory | Completed | Parse errors | Strict accuracy | TP | TN | FP | FN | Final OpenRouter cost | Prompt tokens | Completion tokens | Reasoning tokens | Reported video tokens | Finish reasons |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Gemini Pro | `configs/benchmarks/binary_full_gemini_pro_1080p30fps.json` | `runs/binary_full_gemini_pro_1080p30fps_001` | 257/257 | 0 | 150/257 = 58.4% | 48 | 102 | 94 | 13 | $4.002542 | 793,687 | 201,264 | 186,648 | 654,000 | `stop:257` |
| Qwen | `configs/benchmarks/binary_full_qwen_1080p30fps.json` | `runs/binary_full_qwen_1080p30fps_001` | 257/257 | 0 | 139/257 = 54.1% | 57 | 82 | 114 | 4 | $2.265505 | 6,872,504 | 16,380 | 0 | 0 | `stop:257` |

Outcome breakdown:

| Model | Success accuracy | Failure accuracy |
|---|---:|---:|
| Gemini Pro | 48/61 = 78.7% | 102/196 = 52.0% |
| Qwen | 57/61 = 93.4% | 82/196 = 41.8% |

Task breakdown:

| Model | `basic_vortexing` | `closing_cap` | `vortexing_after_turning_on_vortexer` | `ambiguous_multiple_task` |
|---|---:|---:|---:|---:|
| Gemini Pro | 104/157 = 66.2% | 38/61 = 62.3% | 7/36 = 19.4% | 1/3 = 33.3% |
| Qwen | 97/157 = 61.8% | 28/61 = 45.9% | 14/36 = 38.9% | 0/3 = 0.0% |

Label breakdown:

| Label | Gemini Pro | Qwen |
|---|---:|---:|
| `cap_open` | 28/48 = 58.3% | 15/48 = 31.3% |
| `rack_flipped` | 24/33 = 72.7% | 24/33 = 72.7% |
| `repeated_steps` | 0/1 = 0.0% | 0/1 = 0.0% |
| `tube_drop` | 25/32 = 78.1% | 27/32 = 84.4% |
| `tube_empty` | 5/13 = 38.5% | 1/13 = 7.7% |
| `vortex_off` | 2/27 = 7.4% | 3/27 = 11.1% |
| `wrong_orientation` | 4/12 = 33.3% | 6/12 = 50.0% |
| `wrong_rack` | 15/32 = 46.9% | 6/32 = 18.8% |
| `success:cap_close` | 10/13 = 76.9% | 13/13 = 100.0% |
| `success:clean` | 12/15 = 80.0% | 11/15 = 73.3% |
| `success:correct_rack` | 12/14 = 85.7% | 14/14 = 100.0% |
| `success:tube_nonempty` | 8/8 = 100.0% | 8/8 = 100.0% |
| `success:vortex_on` | 6/11 = 54.5% | 11/11 = 100.0% |

Read: both Gemini Pro and Qwen were parse-clean at `1080px/30fps` across smoke and full runs. Gemini Pro had the better overall strict accuracy and better failure sensitivity than Qwen, but Qwen was much stronger at recognizing success samples. Both models struggled badly with `vortex_off`; Qwen also struggled with `cap_open`, `tube_empty`, and `wrong_rack`. Final full-run costs were $4.002542 for Gemini Pro and $2.265505 for Qwen.

## Candidate Check: GPT-5.5

Updated: 2026-06-14

OpenRouter catalog check: `openai/gpt-5.5` and `openai/gpt-5.5-pro` are listed, but their input modalities are `text`, `image`, and `file`; they are not listed as native `video` input models. Because the benchmark runner sends each sample as video inputs, GPT-5.5 is not currently an apples-to-apples direct-video benchmark candidate through OpenRouter.

Decision: do not run the 5-sample direct-video smoke for GPT-5.5 under the current video benchmark harness. It may still be useful in a separate frame-extraction benchmark where the model receives sampled images/contact sheets instead of video files.

## Smoke: Gemini Pro Multiclass, 10 Samples, 1080px/30fps

Updated: 2026-06-14

Purpose: test the multiclass failure-mode classification prompt with Gemini Pro on the established 10-sample panel: 3 clean successes and 7 failures, one from each major failure folder.

| Metric | Value |
|---|---:|
| Config | `configs/benchmarks/multiclass_10_gemini_pro_1080p30fps.json` |
| Run directory | `runs/multiclass10_gemini_pro_1080p30fps_001` |
| Model | `google/gemini-3.1-pro-preview-20260219` |
| Task | `failure_mode_classification` |
| Media | all available camera views, all videos per sample, max width 1080px, 30fps, CRF 28 |
| Completed | 10/10 |
| API failed calls | 0 |
| Parse errors | 0 |
| Outcome accuracy | 8/10 = 80.0% |
| Exact failure-mode set accuracy | 4/10 = 40.0% |
| Expected failure label included in prediction | 4/10 = 40.0% |
| OpenRouter spend | $0.181944 |
| Prompt tokens | 33,660 |
| Completion tokens | 9,552 |
| Reasoning tokens reported | 8,817 |
| Reported video tokens | 27,000 |
| Finish reasons | `stop:10` |

Per-sample results:

| Sample | Expected | Prediction | Correct outcome | Exact modes |
|---|---|---|---:|---:|
| `success_01_clean` | `success` | `success` | yes | yes |
| `success_02_clean` | `success` | `success` | yes | yes |
| `success_03_clean` | `success` | `success` | yes | yes |
| `fail_cap_loose_01` | `cap_open` | `wrong_rack` | yes | no |
| `fail_tube_drop_01` | `tube_drop` | `wrong_rack` | yes | no |
| `fail_tube_empty_01` | `tube_empty` | `vortex_off` | yes | no |
| `fail_vortex_off_01` | `vortex_off` | `success` | no | no |
| `fail_wrong_orientation_01` | `wrong_orientation` | `success` | no | no |
| `fail_wrong_rack_01` | `wrong_rack` | `wrong_rack` | yes | yes |
| `fail_rack_flipped_01` | `rack_flipped` | `other_failure` | yes | no |

Read: Gemini Pro handled the multiclass JSON format cleanly at `1080px/30fps` with no parse errors. It was good at detecting success versus failure on this panel, but the specific failure labels were noisy: several distinct failure modes collapsed into `wrong_rack` or `vortex_off`, and it missed `vortex_off` plus `wrong_orientation` as successes.

## Full Set: Gemini Flash and Gemini Pro Multiclass, 1080px/30fps

Updated: 2026-06-14

Purpose: run the full 257-sample `failure_mode_classification` benchmark for Gemini Flash and Gemini Pro using the common `1080px/30fps` all-view profile.

| Model | Config | Run directory | Completed | Parse errors | Outcome accuracy | Exact mode accuracy | Expected label included | Final OpenRouter cost | Reasoning tokens | Video tokens | Finish reasons |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Gemini Flash | `configs/benchmarks/multiclass_full_gemini_flash_1080p30fps.json` | `runs/multiclass_full_gemini_flash_1080p30fps_001` | 257/257 | 1 | 142/257 = 55.3% | 93/257 = 36.2% | 98/257 = 38.1% | $3.313478 | 212,989 | 654,000 | `stop:257` |
| Gemini Pro | `configs/benchmarks/multiclass_full_gemini_pro_1080p30fps.json` | `runs/multiclass_full_gemini_pro_1080p30fps_001` | 257/257 | 10 | 154/257 = 59.9% | 82/257 = 31.9% | 91/257 = 35.4% | $4.248082 | 201,459 | 638,700 | `stop:250`, `no_choices:7` |

Outcome breakdown:

| Model | Success outcome accuracy | Failure outcome accuracy | Success exact accuracy | Failure exact accuracy |
|---|---:|---:|---:|---:|
| Gemini Flash | 42/61 = 68.9% | 100/196 = 51.0% | 42/61 = 68.9% | 51/196 = 26.0% |
| Gemini Pro | 44/61 = 72.1% | 110/196 = 56.1% | 44/61 = 72.1% | 38/196 = 19.4% |

Label breakdown, exact mode accuracy:

| Label | Gemini Flash | Gemini Pro |
|---|---:|---:|
| `cap_open` | 22/48 = 45.8% | 9/48 = 18.8% |
| `rack_flipped` | 4/33 = 12.1% | 1/33 = 3.0% |
| `repeated_steps` | 0/1 = 0.0% | 0/1 = 0.0% |
| `tube_drop` | 20/32 = 62.5% | 11/32 = 34.4% |
| `tube_empty` | 0/13 = 0.0% | 1/13 = 7.7% |
| `vortex_off` | 3/27 = 11.1% | 3/27 = 11.1% |
| `wrong_orientation` | 0/12 = 0.0% | 1/12 = 8.3% |
| `wrong_rack` | 2/32 = 6.3% | 12/32 = 37.5% |
| `success:cap_close` | 11/13 = 84.6% | 10/13 = 76.9% |
| `success:clean` | 9/15 = 60.0% | 10/15 = 66.7% |
| `success:correct_rack` | 11/14 = 78.6% | 11/14 = 78.6% |
| `success:tube_nonempty` | 7/8 = 87.5% | 6/8 = 75.0% |
| `success:vortex_on` | 4/11 = 36.4% | 7/11 = 63.6% |

Read: Gemini Pro had slightly better outcome-level multiclass performance, but Gemini Flash had fewer parse errors and better exact failure-mode accuracy overall. Both models remain weak at identifying several specific failure modes, especially `vortex_off`, `rack_flipped`, `tube_empty`, and `wrong_orientation`. Full-run costs were $3.313478 for Gemini Flash and $4.248082 for Gemini Pro.

## Full Set: MiniMax and Qwen Multiclass, 1080px/30fps

Updated: 2026-06-14

Purpose: run the full 257-sample `failure_mode_classification` benchmark for MiniMax and Qwen using the common `1080px/30fps` all-view profile.

| Model | Config | Run directory | Completed | Parse errors | Outcome accuracy | Exact target accuracy | Expected label included | Final OpenRouter cost | Reasoning tokens | Video tokens | Finish reasons |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| MiniMax | `configs/benchmarks/multiclass_full_minimax_1080p30fps.json` | `runs/multiclass_full_minimax_1080p30fps_001` | 257/257 | 3 | 174/257 = 67.7% | 36/257 = 14.0% | 51/257 = 19.8% | $0.970001 | 791 | 0 | `stop:256`, `length:1` |
| Qwen | `configs/benchmarks/multiclass_full_qwen_1080p30fps.json` | `runs/multiclass_full_qwen_1080p30fps_001` | 257/257 | 0 | 127/257 = 49.4% | 69/257 = 26.8% | 87/257 = 33.9% | $2.279913 | 0 | 0 | `stop:257` |

Outcome breakdown:

| Model | Success outcome accuracy | Failure outcome accuracy | Success exact target | Failure exact target |
|---|---:|---:|---:|---:|
| MiniMax | 5/61 = 8.2% | 169/196 = 86.2% | 5/61 = 8.2% | 31/196 = 15.8% |
| Qwen | 57/61 = 93.4% | 70/196 = 35.7% | 57/61 = 93.4% | 12/196 = 6.1% |

Label breakdown, exact target accuracy:

| Label | MiniMax | Qwen |
|---|---:|---:|
| `cap_open` | 1/48 = 2.1% | 5/48 = 10.4% |
| `rack_flipped` | 0/33 = 0.0% | 0/33 = 0.0% |
| `repeated_steps` | 0/1 = 0.0% | 0/1 = 0.0% |
| `tube_drop` | 7/32 = 21.9% | 5/32 = 15.6% |
| `tube_empty` | 0/13 = 0.0% | 0/13 = 0.0% |
| `vortex_off` | 23/27 = 85.2% | 1/27 = 3.7% |
| `wrong_orientation` | 0/12 = 0.0% | 0/12 = 0.0% |
| `wrong_rack` | 0/32 = 0.0% | 1/32 = 3.1% |
| `success:cap_close` | 2/13 = 15.4% | 13/13 = 100.0% |
| `success:clean` | 0/15 = 0.0% | 11/15 = 73.3% |
| `success:correct_rack` | 2/14 = 14.3% | 14/14 = 100.0% |
| `success:tube_nonempty` | 0/8 = 0.0% | 8/8 = 100.0% |
| `success:vortex_on` | 1/11 = 9.1% | 11/11 = 100.0% |

Read: MiniMax is much stronger at outcome-level failure detection, especially `vortex_off`, but remains very weak at recognizing successes and most exact failure labels. Qwen is the opposite: strong success recognition and clean parsing, but weak failure detection and poor exact failure-mode classification. Full-run costs were $0.970001 for MiniMax and $2.279913 for Qwen.

## Single-Choice Multiclass Prompt, 10 Samples, 1080px/30fps

Updated: 2026-06-17

Purpose: test a stricter multiclass prompt where `success` is one of the allowed
multiple-choice labels and each response must return exactly one selected label,
a confidence score, and concise visual reasoning. This task uses
`single_choice_multiclass` rather than the earlier multi-label
`failure_mode_classification` prompt.

Dataset update: generated `metadata/real_human_samples_no_multiple.json`, which
removes the 3 ambiguous `multiple` condition samples:

- `real_human_carrie_multiple_fail_repeated_steps_01`
- `real_human_carrie_multiple_fail_vortex_off_tube_empty_01`
- `real_human_carrie_multiple_fail_vortex_off_tube_empty_02`

Prompt: `prompts/vortexing_single_choice_multiclass.md`

Config: `configs/benchmarks/single_choice_multiclass_10_medium_reasoning_1080p30fps.json`

Run: `runs/single_choice_multiclass10_reasoning512_1080p30fps_001`

Report artifact: `reports/single_choice_multiclass10_reasoning512_1080p30fps/summary.md`

Reasoning setting: OpenRouter rejected sending both `reasoning.effort` and
`reasoning.max_tokens` together. The final benchmark used
`reasoning.max_tokens=512` with `reasoning.exclude=true`, giving a bounded
medium-sized hidden reasoning budget while preserving JSON-only visible output.

MiniMax parse-error retries:

- `runs/single_choice_multiclass10_reasoning512_1080p30fps_minimax_retry1`
- `runs/single_choice_multiclass10_reasoning512_1080p30fps_minimax_retry2`

Parser update: `parse_prediction` now recovers the first valid JSON object from
responses that contain duplicated JSON objects or trailing text. Empty responses
remain parse errors. Re-running the report with this parser recovered 2 MiniMax
rows without additional API calls.

Aggregate results after consolidating successful MiniMax retries and parser
recovery:

| Model | Model ID | Completed | Parse errors | Parser-recovered | Exact choice accuracy | Outcome accuracy | Avg confidence | Reasoning tokens | Cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MiniMax | `minimax/minimax-m3` | 9/10 | 1 | 2 | 10.0% | 20.0% | 0.87 | 8,428 | $0.069408 |
| Gemini Flash | `google/gemini-3.5-flash` | 10/10 | 0 | 0 | 50.0% | 70.0% | 0.96 | 3,656 | $0.095196 |
| Gemini Pro | `google/gemini-3.1-pro-preview-20260219` | 10/10 | 0 | 0 | 40.0% | 70.0% | 0.95 | 3,623 | $0.125644 |
| Qwen | `qwen/qwen3.6-plus` | 10/10 | 0 | 0 | 30.0% | 50.0% | 0.94 | 5,120 | $0.104253 |

Read: Gemini Flash produced the strongest exact single-label accuracy on this
10-sample prompt variant, while Gemini Flash and Gemini Pro tied on outcome
accuracy. MiniMax struggled with the bounded-reasoning setting: 1 row remained
unparseable after two retry attempts plus parser recovery, and the completed predictions were mostly
over-accepting failures as success or labeling successes as `vortex_off`. The
full per-sample table includes each model's output reasoning in the report
artifact.
