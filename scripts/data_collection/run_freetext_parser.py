#!/usr/bin/env python3
"""Run the P6 freetext parser (a text LLM) over a prior P2 (open_detection) run.
task = {operation}_freetext_parser.

Fills the P6 prompt with each P2 output's error_present / observed_errors /
confidence (NOT reasoning) and writes parsed taxonomy labels.
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
    ap.add_argument("--operation", default="vortex", help="operation name; task = {operation}_%s" % PROMPT_TYPE)
    ap.add_argument("--llm", required=True, help="text LLM model name from config/models.yaml")
    ap.add_argument("--p2-run-dir", required=True,
                    help="runs/raw/{operation}_open_detection/{vlm}/{run_id} to parse")
    ap.add_argument("--runs-root", default="runs")
    args = ap.parse_args()
    cfg = runner.load_config()
    runner.run_parser(f"{args.operation}_{PROMPT_TYPE}", args.llm, args.p2_run_dir, cfg,
                      runs_root=args.runs_root)


if __name__ == "__main__":
    main()
