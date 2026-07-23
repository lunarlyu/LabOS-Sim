# VLM evaluation design choices

Development experiment for selecting VLM input and generation settings. This
folder records the sample, active comparisons, and runner. The presentation
report is `../RESULTS.md`; generated evidence is stored in `../artifacts/`.

## Fixed settings

- Dataset catalog: `data/real_human/metadata.jsonl`
- VLM: Gemini 3.1 Pro (`gemini_3_1_pro`) only
- Prompts: P1 closed binary, P2 multilabel, and P3 strict open detection
- P3 normalization: P5 using the pipeline default `gpt_5_5_parser`
- Sampling seed: `20260711`
- Sample: 10 cases from each of the 7 failure modes, plus 10 successes (80 total)
- Temperature: `0`
- Retry policy: retry every failed call, up to 5 retries after the initial call
- Independent-frame JPEG quality: ffmpeg q=10 for every condition (payload-safe)
- Active independent-frame views: fixed to `front,left,right`
- Evaluation prompt/task: hold constant within every paired comparison
- Change one design factor at a time; use the same 80 cases for every condition
- Do not run the vision prompts on any other VLM

The selected cases are in `selected_samples_10_per_type.csv`. Each catalog row
records all five video files for the case. Every active condition uses the fixed
`front,left,right` view set. View selection is not an experimental factor.
The corresponding complete catalog rows are stored once in
`eval/design_choices/artifacts/run_lists/selected_80.jsonl`; every condition references
that canonical run list.

## Exact comparisons

`design_matrix.yaml` records both the historical contact-sheet stage and the
completed independent-frame stage. The runner can reproduce:

| Comparison | A | B | Held-constant baseline |
|---|---:|---:|---|
| Frame budget | 128 uniformly sampled frames | 256 uniformly sampled frames | 3 views, 2048 tokens, 720 px |
| Adaptive frame cap | 128 uniformly sampled frames | `min(source frames, 256)` | 3 views, 2048 tokens, 720 px |
| Adaptive 128 cap | Fixed 128 | `min(source frames, 128)` | 3 views, 2048 tokens, 720 px |
| Hybrid sampler | Fixed 128 | source length if `<128`, 128 if `128--255`, 256 if `>=256` | 3 views, 2048 tokens, 720 px |
| Per-frame resolution | 480 px maximum width | 720 px maximum width | 128 frames, 3 views, 2048 tokens |

The experiment uses 480 versus the repository's 720 px media default.

`frame_budget` is applied per selected camera video. The media pipeline produces
exactly 128 or 256 uniformly timed, chronologically ordered independent JPEG
frames spanning the full clip. If a source contains fewer frames than requested,
FFmpeg duplicates frames to preserve the fixed input shape. The
`frames_adaptive_256` condition instead treats 256 as a per-view maximum: shorter
clips use their source-frame count without duplicate padding, while longer clips
are uniformly sampled to 256 frames.

The `frames_hybrid_128_256` condition uses the minimum decoded length across the
three selected views to choose one shared target for the clip: the minimum
source length below 128, 128 for lengths from 128 through 255, and 256 at or
above 256. Both this condition and `frames_adaptive_128` have completed direct
80-sample evaluations. Neither produced a prompt-consistent improvement over
fixed 128, which remains the selected full-run design.

## Run through the pipeline

Preview all active conditions without API calls:

```bash
.venv/bin/python eval/design_choices/experiment/run_experiment.py --dry-run
```

Run the full experiment:

```bash
.venv/bin/python eval/design_choices/experiment/run_experiment.py --concurrency 1
```

Run one condition with a stable prefix:

```bash
.venv/bin/python eval/design_choices/experiment/run_experiment.py \
  --condition frames_256 --run-prefix vlm_design_01
```

Run only the adaptive 256-frame-cap condition:

```bash
.venv/bin/python eval/design_choices/experiment/run_experiment.py \
  --condition frames_adaptive_256 --run-prefix gemini31pro_adaptive256_design_01
```

Run only the adaptive 128-frame-cap condition:

```bash
.venv/bin/python eval/design_choices/experiment/run_experiment.py \
  --condition frames_adaptive_128 \
  --run-prefix gemini31pro_adaptive128_design_01
```

Run only the hybrid sampler condition:

```bash
.venv/bin/python eval/design_choices/experiment/run_experiment.py \
  --condition frames_hybrid_128_256 \
  --run-prefix gemini31pro_hybrid_design_01
```

Each condition runs all three prompts and changes one baseline
factor. P3 goes through P5 before subtype scoring. Outputs are:

- Raw provider results: `eval/design_choices/artifacts/raw/{run_id}/.../predictions.jsonl`
- Per-call usage/retry metrics: `eval/design_choices/artifacts/raw/{run_id}/.../metrics.jsonl`
- Processed detection tables: `eval/design_choices/artifacts/processed/{run_id}/`
- Accuracy/F1 reports by prompt: `eval/design_choices/artifacts/results/{run_id}/`
- Cost report for only the run IDs selected by the command:
  `eval/design_choices/artifacts/results/<run-prefix>_costs/`

`metrics.jsonl` contains call-level runtime, retries, token usage, and cost.
It is the canonical call-level cost evidence; cost reports retain only the
derived `cost_summary.csv`.
Reports are grouped by task: P1 reports binary and balanced accuracy; P2 and
parsed P3 use exact single-primary-type scoring and per-type statistics. The
three prompts are never averaged into one headline score.

## Reports

- `../RESULTS.md`: presentation-facing tables and the selected design.

Regenerable contact sheets and independent-frame JPEGs are cached locally at
`eval/.cache/design_choices/media/` and are not tracked by Git. A snapshot of the
processed design-study media is also stored in the separate Hugging Face dataset
`labos-sim/eval` under `design_choice_dev_set/media_cache`; the runner can still
regenerate the cache from local source videos when needed.

Historical 80-sample contact-sheet artifacts are retained as the staged
comparison preceding the independent-frame experiment. The runner only creates
independent-frame Gemini 3.1 Pro conditions.
