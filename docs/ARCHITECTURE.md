# LabOS-Sim benchmark — architecture & target layout

Status: target design for the re-organized pipeline (branch `carrie/branching`).
Updated: 2026-06-27. This `docs/` folder is the place for collaborator-facing
design notes.

## Purpose

Test a VLM's ability to identify failure modes in lab-automation videos
(vortexing, to start), turn those judgments into a calibrated evaluation
(SDT-IRT models M1/M2), and package the whole thing as a reproducible benchmark.

Three capability levels (detail in `capability_levels.md`):

- **Easy** — task + success definition + failure-mode taxonomy given (prompts P1, P3).
- **Middle** — task + protocol given, taxonomy withheld; the VLM describes failures
  in free text, which the P6 LLM-parser maps onto the taxonomy (prompt P2 → P6).
- **Hard** — identify the operation and retrieve its protocol before detecting
  failures. Not yet testable (one operation, no full protocols); future work.

## Directory layout

```
LabOS-Sim/
├── README.md
├── requirements.txt
├── .gitignore                      # ignores data/, runs/, __pycache__
│
├── docs/                           # collaborator-facing design notes (versioned)
│   ├── ARCHITECTURE.md             # this file
│   └── capability_levels.md        # the easy/middle/hard framing + current limits
│
├── config/                         # registries only — no per-run files (versioned)
│   ├── models.yaml                 # model registry: id → adapter, provider id, key env, defaults
│   ├── model_costs.json            # pricing fallback table; ships as {} (see Cost section)
│   └── defaults.yaml               # default media policy / run params (overridable by CLI)
│
├── prompts/                        # single source of truth for prompts (versioned)
│   ├── p1_closed_binary.md
│   ├── p2_open_detection.md
│   ├── p3_multilabel_classification.md
│   ├── p6_freetext_subtype_parser.md
│   └── PROMPT_CATALOG.md
│
├── metadata/                       # legacy ground-truth source json (input to build_metadata)
│   └── real_human_samples_no_multiple.json
│
├── data/                           # datasets: videos GITIGNORED, catalogs TRACKED
│   ├── real_human/
│   │   ├── metadata.jsonl          # CATALOG: one DataPoint/line (tracked)
│   │   └── video_<subject>/...     # the .mp4 clips (gitignored)
│   └── *run_list*.jsonl            # selection to run (subset/full), tracked; --data points here
│
├── runs/                           # all run artifacts (GITIGNORED, regenerable)
│   ├── raw/                        # run_id-first: one tree per run
│   │   └── {run_id}/                              # e.g. test_01, full_01
│   │       ├── {task}/{vlm}/                      # P1, P2, P3 (VLM collection)
│   │       │   ├── predictions.jsonl             # incl. ground-truth "expected" per row
│   │       │   ├── metrics.jsonl                 # one CallMetrics row per API call
│   │       │   ├── artifacts/                    # per-call request/response/raw text
│   │       │   └── run_config.json
│   │       └── {task}/{vlm}/{llm}/                # P6 parser (source VLM + parsing LLM)
│   └── processed/                 # digested intermediates, MERGED across run_ids
│       ├── detections_long.csv    # one row per (model, task, sample, subtype) + run_id provenance
│       └── cost_long.csv          # one row per call, flattened from all metrics.jsonl
│
├── results/                        # final deliverables, keyed by ANALYSIS LABEL (versioned)
│   └── {analysis_label}/           # e.g. vortexing_v1 — selects which models/tasks/runs to include
│       ├── model_leaderboard.csv
│       ├── per_model_subtype.csv
│       ├── fit_summary.md
│       ├── cost_summary.csv
│       └── figures/
│
├── scripts/                        # thin CLI entry points (argparse → call into src/)
│   ├── data_ingestion/
│   │   ├── download_real_human.py          # huggingface_hub snapshot → data/ (needs HF_TOKEN)
│   │   └── build_metadata.py               # source json → data/{dataset}/metadata.jsonl
│   ├── data_collection/                    # all take --models, --data run_list.jsonl, --run-id
│   │   ├── run_closed_binary.py            # task=closed_binary            → P1 → VLM
│   │   ├── run_open_detection.py           # task=open_detection           → P2 → VLM (freeform)
│   │   ├── run_multilabel_classification.py# task=multilabel_classification→ P3 → VLM
│   │   └── run_freetext_parser.py          # task=freetext_parser          → P6 → LLM (digests P2)
│   ├── data_processing/
│   │   └── build_flag_table.py             # runs/raw/** → runs/processed/detections_long.csv
│   └── results_rendering/
│       ├── fit_sdt_irt.py                  # detections_long.csv → M1/M2 fit → results/{label}/
│       ├── report_stats.py                 # detections_long.csv → direct (model-free) statistics
│       └── summarize_cost.py               # runs/**/metrics.jsonl → cost_long.csv + cost_summary.csv
│
├── shell_scripts/                  # one-command iteration over models/tasks
│   ├── smoke_test.sh               # cheap live-path validation (1 model, few clips)
│   └── run_full_suite.sh           # all models × tasks → process → render
│
└── src/labos_benchmark/            # the reusable engine (importable package) — kept lean
    ├── __init__.py
    ├── adapters/                   # provider TRANSPORT (how to send video/text per provider)
    │   ├── __init__.py             # get_adapter() dispatch
    │   ├── base.py                 # BaseAdapter + AdapterResult (raw_text, usage, cost_usd, ...)
    │   ├── openai_compatible.py    # GPT / Claude / Qwen via OpenRouter (+ usage.cost passthrough)
    │   ├── gemini.py               # Google native API
    │   └── cosmos_reason.py        # local vLLM server
    ├── client.py                   # unified call layer (≈ brdm llm.py): CallResult + CallMetrics
    │                               #   + pricing + retry/backoff over an adapter
    ├── schemas.py                  # SCHEMA_BY_PROMPT: P1/P3 structured, P2 freeform, P6 parser
    ├── prompts.py                  # load .md, {{key}} fill, PROMPT_BY_TASK + get_prompt_path()
    ├── dataset.py                  # DataPoint dataclass + load_datapoints (metadata/run_list jsonl)
    ├── media.py                    # transcode / contact-sheet / data-uri
    ├── runner.py                   # shared collection loop for VLM tasks AND the P6 parser
    └── io_utils.py                 # IO helpers + setup_keys(_env.json)
```

## Design principles

**Entry points vs. engine.** Everything in `scripts/` is a thin CLI: parse args,
load config, call into `src/labos_benchmark/`, write to `runs/` or `results/`.
All real logic lives in the package. The four `run_*.py` differ only in the
`--task` they pass to a common `runner.collect()`.

**Task is the key that resolves everything.** Task names follow
`{operation}_{prompt_type}` (e.g. `vortex_multilabel_classification`; later
`pipette_multilabel_classification`). The `prompt_type` suffix resolves the prompt
(`prompts.get_prompt_path`) and the schema (`schemas.schema_for_task`); the full
task names the run directory (`runs/raw/{run_id}/{task}/...`). Adding a *prompt type* = add
a prompt + a schema entry + one registry line; adding an *operation* = no new
plumbing, just a new `{operation}_` prefix.

```python
# prompts.py — keyed by prompt_type; split_task() peels {operation} off the front
PROMPT_TYPES = {
    "closed_binary":             "p1_closed_binary.md",
    "open_detection":            "p2_open_detection.md",
    "multilabel_classification": "p3_multilabel_classification.md",
    "freetext_parser":           "p6_freetext_subtype_parser.md",
}
def split_task(task_name) -> tuple[str, str]: ...   # "vortex_closed_binary" -> ("vortex", "closed_binary")
def get_prompt_path(task_name) -> Path: ...
```

**Config holds registries, not runs.** `config/` is just `models.yaml`,
`model_costs.json`, and `defaults.yaml`. Per-run choices (model, task, sample
subset, media policy) are CLI args; the runner writes the resolved config into
each run dir as `run_config.json`, so reproducibility lives with the output, not
in a sprawl of pre-authored config files. (This is why the old
`config/benchmarks/` proliferation is dropped.)

**Run_id-first layout.** `runs/raw/{run_id}/{task}/{vlm}/` (and
`.../{vlm}/{llm}/` for the parser) groups everything from one run under its
`run_id` (e.g. `test_01`, `full_01`), so test vs. full runs are visibly separate.
The `{llm}` level appears only for `freetext_parser`, because P6's output depends
on both the VLM that produced the P2 text and the LLM that parsed it.
`runs/processed/` merges raw runs into tidy tables with `run_id` provenance, so
`results/{analysis_label}/` can integrate across multiple runs rather than being
pinned to one.

**Data is selected by a run list.** The catalog of every clip in a dataset lives
at `data/{dataset}/metadata.jsonl` (one DataPoint per line). A run consumes a
`--data run_list.jsonl` — a subset (10 rows for a test) or the full concatenation
— so the same code runs a smoke test or the whole benchmark. Ground truth travels
in each prediction record's `expected` field, so downstream processing needs no
separate metadata.

**Generated vs. source.** Under `data/`, the `.mp4` videos are gitignored but the
`metadata.jsonl` catalogs and `*run_list*.jsonl` selections are tracked. `runs/` is
gitignored. `config/`, `prompts/`, `data/**/metadata.jsonl`, `docs/`, `results/`,
`scripts/`, `src/` are versioned — the shareable, reproducible benchmark.
(`results/` is the deliverable; `runs/` is the regenerable raw material behind it.)

**Lean package.** `src/labos_benchmark/` deliberately keeps few modules: cost +
call wrapper merged into `client.py`; all schemas in one `schemas.py`; the P6
parser folded into `runner.py`; key loading folded into `io_utils.py`.

## Data flow

```
config/ + prompts/ + data/{dataset}/metadata.jsonl + data/run_list.jsonl   (inputs)
        │
        ▼  scripts/data_collection/run_*.py    (--models, --data run_list, --run-id; via adapters + client)
runs/raw/{run_id}/{task}/{vlm}[/{llm}]/        predictions.jsonl (+ expected) + metrics.jsonl
        │
        ▼  scripts/data_processing/build_flag_table.py   (globs runs/raw/**, truth from records)
runs/processed/detections_long.csv  (+ cost_long.csv)
        │
        ▼  scripts/results_rendering/{fit_sdt_irt.py, report_stats.py, summarize_cost.py}
results/{analysis_label}/   leaderboard, M1/M2 fits, direct stats, cost_summary, figures
```

P6 is a collection step: `run_freetext_parser.py` takes each P2 freeform output,
fills it into the P6 prompt (`{{error_present}}`, `{{observed_errors}}`,
`{{confidence}}`; P2's `reasoning` is intentionally not passed), calls a text LLM,
and writes parsed labels under the same run_id at
`runs/raw/{run_id}/{op}_freetext_parser/{vlm}/{llm}/`. `build_flag_table.py` then
digests both the direct P3 outputs and these parsed-P2 outputs into the same
`detections_long.csv`.

## Data model (DataPoint)

`src/labos_benchmark/dataset.py` defines **`DataPoint`** — one clip: a unified
`index`, `sample_id`, `operation` (task category, e.g. `vortexing`), the
ground-truth `outcome` + `failure_modes`, and its `videos` (camera_view + file
path relative to `data/`). `DataPoint.resolve_videos(data_root, camera_views)`
returns the on-disk paths for the requested angles; `DataPoint.expected` is the
ground-truth label written into each prediction record.

Catalogs (`metadata.jsonl`) and run lists are the same per-line schema, loaded by
`load_datapoints()`. Build a catalog with `scripts/data_ingestion/build_metadata.py`;
make a test run list with e.g. `head -n 10 data/real_human/metadata.jsonl > data/test_run_list.jsonl`.

## Cost & metrics design

Adapted from the `brdm` project's `llm.py`, made transport-agnostic and merged
into `client.py`. Two dataclasses:

- **`CallResult`** (≈ `LLMOutput`): a per-call accumulator — parsed output plus
  `input_tokens`, `output_tokens`, `input_cost`, `output_cost`, `num_retries`,
  `success`, `raw_outputs_per_try`. `register_attempt()` / `register_error()`
  accumulate across retries (a call that retried twice bills for all attempts);
  `total_cost()` rolls it up.
- **`CallMetrics`** (≈ `LLMCallMetrics`): a flat, serializable log row built from a
  `CallResult` (`+ timestamp, runtime, run_id, model`), output dropped. One row per
  call → `runs/raw/.../metrics.jsonl`, so cost per model/task/run is a groupby.

**Pricing is a hybrid, preferred order:**

1. **Provider-reported** `usage.cost` (what `jren/benchmarking` reads from
   OpenRouter's `response["usage"]["cost"]`). Exact dollars; OpenRouter only.
2. **Computed** from `tokens × config/model_costs.json`
   (`{model: {input_cost_per_1M, output_cost_per_1M}}`, what `brdm` does).
   Provider-agnostic fallback for native Gemini / local Cosmos.

`client.py` prefers (1), falls back to (2), and **always records raw `usage`** so
cost can be backfilled. `model_costs.json` ships empty (`{}`) and may later carry
optional `per_image` / `per_video_second` fields (VLM video pricing is not always
pure input-token based).

## Provenance — what came from where

So the lineage of every file is traceable. "imported" = copied with at most
import-path fixes; "adapted" = meaningfully rewritten from a source; "new" =
written for this branch. Sources: **jren-A** = `jren/benchmarking` System A
(`src/labos_benchmark`, `scripts`, `metadata`, `prompts`); **jren-B** =
`jren/benchmarking` `labos-sim-eval`; **brdm** = the `brdm_peer_review` project.

| File in `carrie/branching` | Source | Transfer |
|---|---|---|
| `prompts/p1,p2,p3,p6 + PROMPT_CATALOG.md` | jren-A `prompts/` | imported (these were refined on jren/benchmarking earlier) |
| `metadata/real_human_samples_no_multiple.json` | jren-A `metadata/` | imported (verbatim) |
| `scripts/data_ingestion/download_real_human.py` | jren-A `scripts/download_real_human.py` | imported (verbatim) |
| `src/labos_benchmark/adapters/openai_compatible.py` | jren-B `adapters/openai_compatible.py` | imported (import path fixed) |
| `src/labos_benchmark/adapters/gemini.py` | jren-B `adapters/gemini.py` | imported (import path fixed) |
| `src/labos_benchmark/adapters/cosmos_reason.py` | jren-B `adapters/cosmos_reason.py` | imported (verbatim) |
| `src/labos_benchmark/adapters/base.py` | jren-B `adapters/labos_vlm.py` | adapted (`AdapterResult` + `BaseVLMAdapter`) |
| `src/labos_benchmark/adapters/__init__.py` | — | new (`get_adapter` dispatch) |
| `src/labos_benchmark/dataset.py` | jren-A `src/labos_benchmark/dataset.py` | adapted (rewritten as the `DataPoint` dataclass + jsonl loaders) |
| `scripts/data_ingestion/build_metadata.py` | — | new (source json → metadata.jsonl) |
| `data/{dataset}/metadata.jsonl` | derived from jren-A metadata | generated by build_metadata.py |
| `src/labos_benchmark/media.py` | jren-A `src/labos_benchmark/media.py` | imported (verbatim) |
| `src/labos_benchmark/io_utils.py` | jren-A `io_utils.py` + brdm `utils/env.py` | imported + `setup_keys` appended |
| `src/labos_benchmark/client.py` | brdm `utils/llm.py` | adapted (`LLMOutput`→`CallResult`, `LLMCallMetrics`→`CallMetrics`, `extract_jsons`, retry); made transport-agnostic over adapters |
| `src/labos_benchmark/prompts.py` | brdm `utils/prompt.py` (`fill_in_prompt`) | adapted + new task registry (`PROMPT_TYPES`, `split_task`) |
| `src/labos_benchmark/schemas.py` | jren-A `src/labos_benchmark/schemas.py` | adapted (new taxonomy: `repeated_steps` removed, `additional_failures` + P2/P6 schemas added) |
| `src/labos_benchmark/runner.py` | inspired by jren-A `runner.py` | new (one loop for VLM tasks + the P6 parser) |
| `scripts/data_collection/run_*.py` | pattern from jren-A `scripts/run_benchmark.py` | new (thin CLIs) |
| `scripts/data_processing/build_flag_table.py` | local working-tree script (was untracked) | refined here (multi-run glob, new taxonomy, provenance cols) |
| `scripts/results_rendering/fit_sdt_irt.py` | local working-tree script (was untracked) | refined here (reads the flag table; new taxonomy) |
| `scripts/results_rendering/report_stats.py` | — | new |
| `scripts/results_rendering/summarize_cost.py` | — | new |
| `config/models.yaml` | jren-B `config.yaml` (model list) | adapted into a registry |
| `config/defaults.yaml`, `config/model_costs.json` | — | new |
| `docs/*` | — | new |
