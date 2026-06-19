# LabOS-Sim

## Hugging Face Dataset Setup

This project uses Hugging Face tooling to download the `labos-sim/real_human`
dataset into `data/real_human`.

From WSL Ubuntu:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_real_human.py
```

Generate initial path-derived sample metadata:

```bash
python scripts/generate_real_human_metadata.py
```

The generated metadata separates success states into task families:
`basic_vortexing`, `closing_cap`, and `vortexing_after_turning_on_vortexer`.

## Benchmarking

The canonical full-study setup is all camera views, all videos per sample, the
`1080px/30fps` derived-video profile, temperature 0, exact OpenRouter model
IDs, JSON-only responses, and local parse validation. Parsed predictions must
include a numeric `confidence` field in `[0, 1]`; missing or invalid confidence
is treated as a parse error.

Run a dry benchmark pass without calling an API:

```bash
python scripts/run_benchmark.py --dry-run --model REPLACE_WITH_OPENROUTER_VIDEO_MODEL_ID --limit 2
```

Run against OpenRouter after setting an API key:

```bash
cp .env.example .env
# Fill in OPENROUTER_API_KEY in .env
python scripts/run_benchmark.py --model provider/model-id --limit 5
```

Benchmark outputs are written under `runs/`. Each run checkpoints config,
manifest rows, redacted request payloads, raw responses, predictions, errors,
and `state.json` as it proceeds.

The local parser first attempts strict JSON parsing. If a model returns a valid
JSON object followed by duplicate JSON or trailing text, the parser recovers the
first complete object and still applies the task schema validator. Empty or
structurally invalid outputs remain parse errors.

The current cross-model visual input profile for full studies is
`canonical_clip_1080px_30fps`: all selected camera videos are converted to MP4
clips at 1080px width and 30 fps, with the same derived clips sent to each
model.

### Canonical Full-Study Runbook

Run the 20-sample smoke config for a model first. If there are no parse errors,
run the matching full config.

```bash
python scripts/run_benchmark.py --config configs/benchmarks/binary_20_gemini_flash_1080p30fps.json --run-id binary20_gemini_flash_1080p30fps_001
python scripts/run_benchmark.py --config configs/benchmarks/binary_full_gemini_flash_1080p30fps.json --run-id binary_full_gemini_flash_1080p30fps_001
```

The active full binary configs are:

- `configs/benchmarks/binary_full_gemini_flash_1080p30fps.json`
- `configs/benchmarks/binary_full_gemini_pro_1080p30fps.json`
- `configs/benchmarks/binary_full_minimax_1080p30fps.json`
- `configs/benchmarks/binary_full_qwen_1080p30fps.json`

The active full multiclass configs are:

- `configs/benchmarks/multiclass_full_gemini_flash_1080p30fps.json`
- `configs/benchmarks/multiclass_full_gemini_pro_1080p30fps.json`
- `configs/benchmarks/multiclass_full_minimax_1080p30fps.json`
- `configs/benchmarks/multiclass_full_qwen_1080p30fps.json`

After the full runs finish, rerun failed rows with the canonical two-retry
consolidation step:

```bash
python scripts/retry_failed_full_benchmarks.py
```

This script retries rows from `errors.jsonl` and non-completed
`predictions.jsonl` entries up to two times, writes retry configs under
`runs/retry_configs/`, writes retry run directories under `runs/`, and writes a
consolidated report to `runs/retry_consolidation_full_1080p30fps.json`. Report
tables should use the consolidated metrics and total cost after retries, while
keeping original run directories in `benchmark_tracking.md` for auditability.

Retry any completed rows that still lack valid confidence scores:

```bash
python scripts/retry_missing_confidence_full_benchmarks.py
```

This writes `runs/confidence_retry_full_1080p30fps.json`. The AUROC step below
automatically merges successful confidence-retry rows when this artifact exists.

Calculate success-positive AUROC from the retry-consolidated rows:

```bash
python scripts/calculate_full_auroc.py
```

The AUROC script writes `runs/auroc_full_1080p30fps.json`. It uses
`confidence` as the score for predicted-success rows and `1 - confidence` as
the score for predicted-failure rows.

Generate the full comparison report, CSV tables, and SVG charts:

```bash
python scripts/report_full_benchmark_comparison.py
```

This writes the report bundle under `reports/full_1080p30fps/`, including
overall binary and multiclass summaries, per-category metrics, cost charts, and
SVG plots suitable for papers or lab notes.

The default Gemini smoke configs use small transcoded API copies because local
videos must be sent as base64 data URLs. To attempt original, untranscoded MP4s,
use:

```bash
python scripts/run_benchmark.py --config configs/benchmarks/vortexing_openrouter_gemini_success_variants_full_video.json
```

This preserves the original MP4s, but large multi-view requests may be rejected
by OpenRouter/provider request-size limits.

If the dataset is private, log in first:

```bash
huggingface-cli login
```
