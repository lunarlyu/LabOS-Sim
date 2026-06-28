#!/usr/bin/env python3
"""Run the closed-binary task (P1) against one or more VLMs.
task = {operation}_closed_binary.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from labos_benchmark import runner  # noqa: E402

PROMPT_TYPE = "closed_binary"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--operation", default="vortex", help="task = {operation}_%s" % PROMPT_TYPE)
    ap.add_argument("--models", nargs="+", required=True,
                    help="one or more model names from config/models.yaml")
    ap.add_argument("--camera-views", nargs="*", default=None,
                    help="subset of angles, e.g. front gripper (default: all)")
    ap.add_argument("--concurrency", type=int, default=1, help="parallel clips per model")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--runs-root", default="runs")
    args = ap.parse_args()

    cfg = runner.load_config()
    task = f"{args.operation}_{PROMPT_TYPE}"
    for model in args.models:
        runner.collect(task, model, cfg, limit=args.limit,
                       camera_views=args.camera_views, concurrency=args.concurrency,
                       runs_root=args.runs_root)


if __name__ == "__main__":
    main()
