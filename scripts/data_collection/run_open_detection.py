#!/usr/bin/env python3
"""Run the open-detection task (P2) against a VLM. task = {operation}_open_detection.

P2 is freeform; its output is later mapped to the taxonomy by run_freetext_parser.py (P6).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from labos_benchmark import runner  # noqa: E402

PROMPT_TYPE = "open_detection"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--operation", default="vortex", help="operation name; task = {operation}_%s" % PROMPT_TYPE)
    ap.add_argument("--model", required=True, help="model name from config/models.yaml")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--runs-root", default="runs")
    args = ap.parse_args()
    cfg = runner.load_config()
    runner.collect(f"{args.operation}_{PROMPT_TYPE}", args.model, cfg,
                   limit=args.limit, runs_root=args.runs_root)


if __name__ == "__main__":
    main()
