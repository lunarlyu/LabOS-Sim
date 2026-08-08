#!/usr/bin/env python3
"""Run the Gemini VLM design-choice experiment through the full pipeline."""
from __future__ import annotations

import argparse
import copy
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from labos_benchmark import runner  # noqa: E402

MODEL = "gemini_3_1_pro"
PARSER_MODEL = "gpt_5_5_parser"
SAMPLES_PER_TYPE = 10
N_CLASSES = 8
EXPECTED_SAMPLES = SAMPLES_PER_TYPE * N_CLASSES
SELECTION_MANIFEST = EXPERIMENT_DIR / "selected_samples_10_per_type.csv"
TASKS = [
    "vortex_closed_binary",              # P1
    "vortex_multilabel_classification",  # P2
    "vortex_open_detection_strict",      # P3; normalized by P5 below
]
PARSER_TASK = "vortex_open_detection_strict_parser"
RUNS_ROOT = Path("design_justification/eval_design_choices")

CONDITIONS = {
    "baseline_f128_views3_tok2048_res720": {
        "frame_count": 128,
        "views": ["front", "left", "right"], "tokens": 2048, "resolution": 720,
    },
    "frames_256": {
        "frame_count": 256,
        "views": ["front", "left", "right"], "tokens": 2048, "resolution": 720,
    },
    "frames_adaptive_256": {
        "frame_count": 256, "cap_at_source": True,
        "views": ["front", "left", "right"], "tokens": 2048, "resolution": 720,
    },
    "resolution_480": {
        "frame_count": 128,
        "views": ["front", "left", "right"], "tokens": 2048, "resolution": 480,
    },
    # View ablation: input cost scales linearly with view count, so if fewer
    # views hold accuracy, every future run (incl. the multi-model roster)
    # gets proportionally cheaper. Compare against the committed 3-view
    # baseline run. Not part of the original staged comparisons.
    # Frame-budget bridge (downward): literature norms are ~1-4 fps (Video-MME,
    # Gemini native sampling, LLaVA-Video's 64-frame cap), so 128/view on 4-21s
    # clips is far above convention. If 32/view holds accuracy, every future
    # run costs ~1/4 and Claude's ~100-image cap fits 3 views (96 images).
    # Risk to watch per-subtype: vortex_off / tube_drop (motion & brief events).
    "frames_64": {
        "frame_count": 64,
        "views": ["front", "left", "right"], "tokens": 2048, "resolution": 720,
    },
    "frames_32": {
        "frame_count": 32,
        "views": ["front", "left", "right"], "tokens": 2048, "resolution": 720,
    },
    "views_front_left": {
        "frame_count": 128,
        "views": ["front", "left"], "tokens": 2048, "resolution": 720,
    },
    "views_front_only": {
        "frame_count": 128,
        "views": ["front"], "tokens": 2048, "resolution": 720,
    },
}


def build_run_list(output: Path) -> int:
    with SELECTION_MANIFEST.open(newline="", encoding="utf-8") as f:
        manifest_rows = list(csv.DictReader(f))
    wanted = {row["sample_id"] for row in manifest_rows}
    group_counts: dict[str, int] = {}
    for row in manifest_rows:
        label = row["selection_group"]
        group_counts[label] = group_counts.get(label, 0) + 1
    if len(wanted) != EXPECTED_SAMPLES or set(group_counts.values()) != {SAMPLES_PER_TYPE}:
        raise SystemExit(
            f"invalid selection manifest: expected {N_CLASSES} groups x {SAMPLES_PER_TYPE} "
            f"unique samples; found {len(wanted)} samples and counts {group_counts}"
        )
    catalog_path = REPO_ROOT / "data/real_human/metadata.jsonl"
    catalog = [
        json.loads(line)
        for line in catalog_path.read_text().splitlines()
        if line.strip()
    ]
    selected = [row for row in catalog if row["sample_id"] in wanted]
    missing = wanted - {row["sample_id"] for row in selected}
    if missing:
        raise SystemExit(f"selected sample IDs missing from catalog: {sorted(missing)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row) + "\n" for row in selected), encoding="utf-8")
    return len(selected)


PROVIDERS = {
    # Historical/default: Luna's OpenRouter key; provider-reported billing.
    "openrouter": {"base_url_env": "OPENROUTER_BASE_URL",
                   "api_key_env": "OPENROUTER_API_KEY",
                   "provider_model_id": "google/gemini-3.1-pro-preview"},
    # Carrie's Arena key (OpenAI-compatible). Arena returns no usage.cost, so
    # config_for injects table pricing for cost recording.
    "arena": {"base_url": "https://api.preview.arena.ai/v1",
              "api_key_env": "ARENA_API_KEY",
              "provider_model_id": "gemini-3.1-pro-preview"},
}


def config_for(base: dict, condition: dict, provider_name: str = "openrouter") -> dict:
    cfg = copy.deepcopy(base)
    defaults = cfg.setdefault("defaults", {})
    call = defaults.setdefault("call", {})
    call["max_retries"] = 5
    call["max_completion_tokens"] = condition["tokens"]
    media = defaults.setdefault("media", {})
    media["input_type"] = "image_frames"
    preprocess = media.setdefault("preprocess", {})
    frames = preprocess.setdefault("frames", {})
    frames.update({
        "frame_count": condition["frame_count"],
        "cap_at_source": condition.get("cap_at_source", False),
        "max_width": condition["resolution"],
        "quality": 10,
    })
    # Pin the experiment transport independently of the shared full-run model
    # registry. Historical design runs used Gemini through OpenRouter; keeping
    # these fields local prevents unrelated registry edits from changing the
    # provider midway through a resumable run.
    provider = PROVIDERS[provider_name]
    cfg["models"][MODEL].update({
        "adapter": "gemini",
        "provider_model_id": provider["provider_model_id"],
        "api_style": "openai_compatible",
        "media_transport": "data_uri",
        "temperature": 0,
        "max_completion_tokens": condition["tokens"],
        **({"base_url": provider["base_url"]} if "base_url" in provider
           else {"base_url_env": provider["base_url_env"]}),
        "api_key_env": provider["api_key_env"],
    })
    if provider_name == "arena":
        cfg.setdefault("model_costs", {}).setdefault(
            "gemini-3.1-pro-preview",
            {"input_cost_per_1M": 2.0, "output_cost_per_1M": 12.0})
    return cfg


def process_metrics(run_id: str, runs_root: Path, results_root: Path) -> None:
    processed = runs_root / "processed" / run_id
    result_dir = results_root / run_id
    subprocess.run([
        sys.executable, "scripts/data_processing/build_detection_table.py",
        "--runs-root", str(runs_root), "--run-ids", run_id,
        "--outdir", str(processed),
    ], cwd=REPO_ROOT, check=True)
    subprocess.run([
        sys.executable, "scripts/results_rendering/report_stats.py",
        "--table", str(processed / "detections_long.csv"),
        "--by-task", "--outdir", str(result_dir),
    ], cwd=REPO_ROOT, check=True)


def require_complete(run_dir: Path, expected: int) -> None:
    """Stop the experiment before metrics if any sample is still unsuccessful."""
    predictions = run_dir / "predictions.jsonl"
    completed = runner.successful_sample_ids(predictions)
    if len(completed) != expected:
        missing = expected - len(completed)
        raise SystemExit(
            f"incomplete run: {run_dir} has {len(completed)}/{expected} successful samples "
            f"({missing} missing). Rerun the same command to retry only failures; "
            "metrics were not generated for this incomplete condition."
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--condition", action="append", choices=sorted(CONDITIONS),
                    help="run only this condition; repeatable (default: all conditions)")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None,
                    help="run only the first N selected samples (for validation)")
    ap.add_argument("--run-prefix", default=None)
    ap.add_argument("--provider", choices=sorted(PROVIDERS), default="openrouter",
                    help="API route/billing for the VLM (parser stays on OpenRouter)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.limit is not None and not 1 <= args.limit <= EXPECTED_SAMPLES:
        raise SystemExit(f"--limit must be between 1 and {EXPECTED_SAMPLES}")
    expected_run_samples = args.limit or EXPECTED_SAMPLES

    stamp = args.run_prefix or datetime.now(timezone.utc).strftime("vlm_design_%Y%m%dT%H%M%SZ")
    names = args.condition or list(CONDITIONS)
    runs_root = REPO_ROOT / RUNS_ROOT
    results_root = runs_root / "results"
    run_list = runs_root / "run_lists" / f"{stamp}_selected_{EXPECTED_SAMPLES}.jsonl"

    print(f"vlm={MODEL} parser={PARSER_MODEL} input_mode=image_frames tasks={','.join(TASKS)} "
          f"samples={expected_run_samples}"
          + (f" (validation subset of {EXPECTED_SAMPLES})" if args.limit else
             f" ({SAMPLES_PER_TYPE}/type)"))
    for name in names:
        print(f"{stamp}_{name}: {json.dumps(CONDITIONS[name])}")
    if args.dry_run:
        return

    import os
    if args.provider == "arena" and not os.environ.get("ARENA_API_KEY"):
        token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if not token:
            raise SystemExit("arena provider needs ARENA_API_KEY or ANTHROPIC_AUTH_TOKEN")
        os.environ["ARENA_API_KEY"] = token
    count = build_run_list(run_list)
    if count != EXPECTED_SAMPLES:
        raise SystemExit(f"expected {EXPECTED_SAMPLES} selected cases, found {count}")
    base = runner.load_config()
    if MODEL not in base["models"]:
        raise SystemExit(f"model not found in config/models.yaml: {MODEL}")
    completed_run_ids = []
    for name in names:
        run_id = f"{stamp}_{name}"
        condition = CONDITIONS[name]
        cfg = config_for(base, condition, args.provider)
        run_dirs = {}
        for task in TASKS:
            run_dirs[task] = runner.collect(
                task, MODEL, cfg, run_id=run_id,
                data_list=run_list, camera_views=condition["views"],
                limit=args.limit, concurrency=args.concurrency, runs_root=runs_root,
                data_root=REPO_ROOT / "data",
            )
            require_complete(run_dirs[task], expected_run_samples)
        # P3 does not emit canonical failure_modes. Normalize it through P5
        # using the repository's default parser model from run_full_suite.sh.
        parser_cfg = copy.deepcopy(cfg)
        parser_cfg["defaults"]["call"]["max_completion_tokens"] = 2048
        parser_run_dir = runner.run_parser(
            PARSER_TASK, PARSER_MODEL, run_dirs["vortex_open_detection_strict"],
            parser_cfg, run_id=run_id, concurrency=args.concurrency,
            runs_root=runs_root,
        )
        require_complete(parser_run_dir, expected_run_samples)
        process_metrics(run_id, runs_root, results_root)
        completed_run_ids.append(run_id)

    cost_cmd = [
        sys.executable, "scripts/results_rendering/summarize_cost.py",
        "--runs-root", str(runs_root),
        "--outdir", str(results_root / f"{stamp}_costs"),
    ]
    for run_id in completed_run_ids:
        cost_cmd.extend(["--run-id", run_id])
    subprocess.run(cost_cmd, cwd=REPO_ROOT, check=True)
    print(f"raw: {runs_root / 'raw'}")
    print(f"metrics: {results_root}")


if __name__ == "__main__":
    main()
