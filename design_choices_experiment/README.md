# VLM evaluation design choices

Development experiment for selecting VLM input and generation settings. This
folder records the sample, active comparisons, and results. All generated
artifacts are isolated under the top-level `eval_design_choices/` directory.

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

## Exact comparisons

`design_matrix.yaml` records both the historical contact-sheet stage and the
active independent-frame stage. The active runner compares:

| Comparison | A | B | Held-constant baseline |
|---|---:|---:|---|
| Frame budget | 128 uniformly sampled frames | 256 uniformly sampled frames | 3 views, 2048 tokens, 720 px |
| Adaptive frame cap | 128 uniformly sampled frames | `min(source frames, 256)` | 3 views, 2048 tokens, 720 px |
| Per-frame resolution | 480 px maximum width | 720 px maximum width | 128 frames, 3 views, 2048 tokens |

The experiment uses 480 versus the repository's 720 px media default.

`frame_budget` is applied per selected camera video. The media pipeline produces
exactly 128 or 256 uniformly timed, chronologically ordered independent JPEG
frames spanning the full clip. If a source contains fewer frames than requested,
FFmpeg duplicates frames to preserve the fixed input shape. The
`frames_adaptive_256` condition instead treats 256 as a per-view maximum: shorter
clips use their source-frame count without duplicate padding, while longer clips
are uniformly sampled to 256 frames.

## Run through the pipeline

Preview all active conditions without API calls:

```bash
.venv/bin/python design_choices_experiment/run_experiment.py --dry-run
```

Run the full experiment:

```bash
.venv/bin/python design_choices_experiment/run_experiment.py --concurrency 1
```

Run one condition with a stable prefix:

```bash
.venv/bin/python design_choices_experiment/run_experiment.py \
  --condition frames_256 --run-prefix vlm_design_01
```

Run only the adaptive 256-frame-cap condition:

```bash
.venv/bin/python design_choices_experiment/run_experiment.py \
  --condition frames_adaptive_256 --run-prefix gemini31pro_adaptive256_design_01
```

Each condition runs all three prompts and changes one baseline
factor. P3 goes through P5 before subtype scoring. Outputs are:

- Raw provider results: `eval_design_choices/raw/{run_id}/.../predictions.jsonl`
- Per-call usage/retry metrics: `eval_design_choices/raw/{run_id}/.../metrics.jsonl`
- Processed detection tables: `eval_design_choices/processed/{run_id}/`
- Accuracy/F1 reports by prompt: `eval_design_choices/results/{run_id}/`
- Aggregated cost report: `eval_design_choices/processed/costs/`

`metrics.jsonl` contains call-level runtime, retries, token usage, and cost.
Reports are grouped by task: P1 reports binary and balanced accuracy; P2 and
parsed P3 use exact single-primary-type scoring and per-type statistics. The
three prompts are never averaged into one headline score.

## Reports

- `design_choice_results_brief.md`: presentation-facing tables.

Historical 80-sample contact-sheet artifacts are retained as the staged
comparison preceding the active independent-frame experiment. The active runner
only creates independent-frame Gemini 3.1 Pro conditions.
