#!/usr/bin/env python3
"""Aggregate per-call cost across all runs.

Reads every runs/raw/**/metrics.jsonl, writes:
  runs/processed/cost_long.csv     one row per call (with task, model, run_id)
  runs/processed/cost_summary.csv  totals per (task, model)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-root", default="runs")
    ap.add_argument("--outdir", default="runs/processed")
    args = ap.parse_args(argv)

    raw = Path(args.runs_root) / "raw"
    rows = []
    for mp in raw.glob("**/metrics.jsonl"):
        rel = mp.relative_to(raw)            # {task}/.../{run_id}/metrics.jsonl
        task = rel.parts[0]
        run_id = mp.parent.name
        for line in mp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            d["task"] = task
            d["run_id"] = run_id
            rows.append(d)

    if not rows:
        print(f"[cost] no metrics.jsonl found under {raw}")
        return

    df = pd.DataFrame(rows)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df.to_csv(outdir / "cost_long.csv", index=False)

    summ = (
        df.groupby(["task", "model"])
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
