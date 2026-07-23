#!/usr/bin/env python3
"""Run the STRICT parser (P5) — a text LLM over a prior P3 (open_detection_strict) run.
task = {operation}_open_detection_strict_parser.

Maps each P3 output's comma-separated observed_errors onto the taxonomy. Output
goes under the same run_id at
runs/raw/{run_id}/{op}_open_detection_strict_parser/{vlm}/{llm}/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from labos_benchmark import runner  # noqa: E402

PROMPT_TYPE = "open_detection_strict_parser"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--operation", default="vortex", help="task = {operation}_%s" % PROMPT_TYPE)
    ap.add_argument("--llms", nargs="+", required=True,
                    help="one or more text-LLM model names from config/models.yaml")
    ap.add_argument("--source-run-dir", required=True,
                    help="runs/raw/{run_id}/{op}_open_detection_strict/{vlm} to parse")
    ap.add_argument("--run-id", default=None, help="override run_id (default: inferred from source)")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--runs-root", default=runner.DEFAULT_RUNS_ROOT)
    args = ap.parse_args()

    cfg = runner.load_config()
    task = f"{args.operation}_{PROMPT_TYPE}"
    for llm in args.llms:
        runner.run_parser(task, llm, args.source_run_dir, cfg, run_id=args.run_id,
                          concurrency=args.concurrency, runs_root=args.runs_root)


if __name__ == "__main__":
    main()
