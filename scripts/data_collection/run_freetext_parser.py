#!/usr/bin/env python3
"""Run the P6 freetext parser (text LLM) over a prior P2 (open_detection) run.
task = {operation}_freetext_parser.

Fills the P6 prompt with each P2 output's error_present / observed_errors /
confidence (NOT reasoning) and writes parsed taxonomy labels. Output is placed
under the same run_id at runs/raw/{run_id}/{op}_freetext_parser/{vlm}/{llm}/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from labos_benchmark import runner  # noqa: E402

PROMPT_TYPE = "freetext_parser"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--operation", default="vortex", help="task = {operation}_%s" % PROMPT_TYPE)
    ap.add_argument("--llms", nargs="+", required=True,
                    help="one or more text-LLM model names from config/models.yaml")
    ap.add_argument("--p2-run-dir", required=True,
                    help="runs/raw/{run_id}/{operation}_open_detection/{vlm} to parse")
    ap.add_argument("--run-id", default=None,
                    help="override run_id (default: inferred from --p2-run-dir)")
    ap.add_argument("--concurrency", type=int, default=1, help="parallel rows per LLM")
    ap.add_argument("--runs-root", default="runs")
    args = ap.parse_args()

    cfg = runner.load_config()
    task = f"{args.operation}_{PROMPT_TYPE}"
    for llm in args.llms:
        runner.run_parser(task, llm, args.p2_run_dir, cfg, run_id=args.run_id,
                          concurrency=args.concurrency, runs_root=args.runs_root)


if __name__ == "__main__":
    main()
