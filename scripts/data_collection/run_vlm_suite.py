#!/usr/bin/env python3
"""Run the VLM prompt suite (default P1+P2+P3) clip-grouped, for prompt caching.

Unlike the per-task run_*.py scripts (one full dataset pass per prompt), this
sends each clip's prompts back-to-back so their identical media prefix — ~99%
of input tokens at the full frame design — can hit the provider's implicit
prompt cache. Requires a route pinned to a single provider backend (e.g.
gemini_3_1_pro_or); verify cache behavior first with
scripts/probe_prompt_cache.py.

Outputs are identical to the per-task scripts (runs/raw/{run_id}/{task}/{vlm}/
per task), so scoring and the P5 parser pipeline are unaffected.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from labos_benchmark import runner  # noqa: E402

DEFAULT_PROMPT_TYPES = ["closed_binary", "multilabel_classification", "open_detection_strict"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--operation", default="vortex",
                    help="tasks = {operation}_{prompt_type}")
    ap.add_argument("--prompt-types", nargs="+", default=DEFAULT_PROMPT_TYPES,
                    help="VLM prompt types to run per clip, in call order "
                         "(default: %(default)s)")
    ap.add_argument("--models", nargs="+", required=True,
                    help="one or more model names from config/models.yaml")
    ap.add_argument("--data", required=True,
                    help="run_list.jsonl under data/ (subset for test, full for full run)")
    ap.add_argument("--run-id", default=None,
                    help="label grouping this run, e.g. test_01 (default: UTC timestamp)")
    ap.add_argument("--camera-views", nargs="*", default=None,
                    help="subset of angles, e.g. front left right (default: configured views)")
    ap.add_argument("--concurrency", type=int, default=1, help="parallel clips per model")
    ap.add_argument("--limit", type=int, default=None, help="cap number of datapoints")
    ap.add_argument("--runs-root", default="runs")
    ap.add_argument("--data-root", default="data")
    args = ap.parse_args()

    cfg = runner.load_config()
    run_id = args.run_id or runner.default_run_id()
    tasks = [f"{args.operation}_{ptype}" for ptype in args.prompt_types]
    for model in args.models:
        runner.collect_suite(tasks, model, cfg, run_id=run_id, data_list=args.data,
                             camera_views=args.camera_views, limit=args.limit,
                             concurrency=args.concurrency, runs_root=args.runs_root,
                             data_root=args.data_root)


if __name__ == "__main__":
    main()
