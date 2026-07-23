#!/usr/bin/env python3
"""Aggregate per-call cost across all or selected runs.

Reads every eval/runs/raw/**/metrics.jsonl and writes:
  eval/runs/processed/cost_summary.csv  totals per (run_id, task, model)

The raw metrics.jsonl files are the canonical call-level evidence, so this
script intentionally does not duplicate them into a cost_long.csv.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

EVAL_ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-root", default=EVAL_ROOT / "runs")
    ap.add_argument("--outdir", default=EVAL_ROOT / "runs/processed")
    ap.add_argument(
        "--run-id", action="append", dest="run_ids",
        help="include only this run ID; repeatable (default: all run IDs)",
    )
    args = ap.parse_args(argv)

    raw = Path(args.runs_root) / "raw"
    selected_run_ids = set(args.run_ids or [])
    rows = []
    for mp in raw.glob("**/metrics.jsonl"):
        rel = mp.relative_to(raw)            # {run_id}/{task}/{vlm}[/{llm}]/metrics.jsonl
        run_id = rel.parts[0]
        if selected_run_ids and run_id not in selected_run_ids:
            continue
        task = rel.parts[1] if len(rel.parts) > 1 else ""
        for line in mp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            d.setdefault("run_id", run_id)
            d["task"] = task
            rows.append(d)

    if not rows:
        scope = f" for run IDs {sorted(selected_run_ids)}" if selected_run_ids else ""
        print(f"[cost] no metrics.jsonl found under {raw}{scope}")
        return

    df = pd.DataFrame(rows)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    summ = (
        df.groupby(["run_id", "task", "model"])
        .agg(calls=("cost", "size"), total_cost_usd=("cost", "sum"),
             input_tokens=("input_tokens", "sum"), output_tokens=("output_tokens", "sum"))
        .reset_index()
        .sort_values("total_cost_usd", ascending=False)
    )
    summ.to_csv(outdir / "cost_summary.csv", index=False)
    print(summ.to_string(index=False))
    print(f"[cost] grand total: ${df['cost'].sum():.4f} across {len(df)} calls")


if __name__ == "__main__":
    main()
