#!/usr/bin/env python3
"""Run open-detection STRICT (P3) against one or more VLMs — error-aware.
task = {operation}_open_detection_strict. The VLM is told to detect errors and
list them succinctly; map to the taxonomy later with run_open_detection_strict_parser.py (P5).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from labos_benchmark import runner  # noqa: E402

PROMPT_TYPE = "open_detection_strict"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--operation", default="vortex", help="task = {operation}_%s" % PROMPT_TYPE)
    ap.add_argument("--models", nargs="+", required=True,
                    help="one or more model names from config/models.yaml")
    ap.add_argument("--data", required=True, help="run_list.jsonl under data/")
    ap.add_argument("--run-id", default=None, help="label grouping this run (default: UTC timestamp)")
    ap.add_argument("--camera-views", nargs="*", default=None, help="subset of angles (default: all)")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--runs-root", default="runs")
    ap.add_argument("--data-root", default="data")
    args = ap.parse_args()

    cfg = runner.load_config()
    run_id = args.run_id or runner.default_run_id()
    task = f"{args.operation}_{PROMPT_TYPE}"
    for model in args.models:
        runner.collect(task, model, cfg, run_id=run_id, data_list=args.data,
                       camera_views=args.camera_views, limit=args.limit,
                       concurrency=args.concurrency, runs_root=args.runs_root,
                       data_root=args.data_root)


if __name__ == "__main__":
    main()
