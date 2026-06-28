#!/usr/bin/env python3
"""Direct (non-Bayesian) statistics from the flag table.

Reads runs/processed/detections_long.csv and reports, per model (optionally split by
task), the headline classification metrics — a model-free complement to the
SDT-IRT fit (fit_sdt_irt.py). These are the "report direct statistics from the
table" deliverable.

Outputs (to --outdir, default results/direct_stats):
  per_model_outcome.csv   outcome accuracy, success/failure recall, balanced acc,
                          failure AUROC (if confidence present), macro-F1
  per_subtype_stats.csv   per (model, subtype): recall, precision, F1, FPR
  direct_stats.md         human-readable summary
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def _auroc(labels: np.ndarray, scores: np.ndarray) -> float:
    """Rank-based AUROC (Mann-Whitney). NaN if a class is absent or scores missing."""
    mask = ~np.isnan(scores)
    labels, scores = labels[mask], scores[mask]
    n_pos = int(labels.sum())
    n_neg = int((1 - labels).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = scores.argsort(kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts)); np.add.at(sums, inv, ranks)
    ranks = (sums / counts)[inv]
    auc = (ranks[labels == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return float(auc)


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall and not np.isnan(precision) and not np.isnan(recall) else
          (0.0 if (tp + fp + fn) else float("nan")))
    return recall, precision, f1


def per_subtype_stats(long: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    out = []
    for keys, d in long.groupby(group_cols + ["subtype"], sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        tp = int(((d.is_present == 1) & (d.flagged == 1)).sum())
        fp = int(((d.is_present == 0) & (d.flagged == 1)).sum())
        fn = int(((d.is_present == 1) & (d.flagged == 0)).sum())
        tn = int(((d.is_present == 0) & (d.flagged == 0)).sum())
        recall, precision, f1 = _prf(tp, fp, fn)
        row = dict(zip(group_cols + ["subtype"], keys))
        row.update(n_present=tp + fn, n_absent=fp + tn, tp=tp, fp=fp, fn=fn,
                   recall=recall, precision=precision, f1=f1,
                   fpr=(fp / (fp + tn) if (fp + tn) else float("nan")))
        out.append(row)
    return pd.DataFrame(out)


def per_model_outcome(long: pd.DataFrame, subtype_df: pd.DataFrame,
                      group_cols: list[str]) -> pd.DataFrame:
    # outcome-level: one row per (group, sample) — dedupe the subtype expansion
    one = long.drop_duplicates(subset=group_cols + ["sample_id"]).copy()
    out = []
    for keys, d in one.groupby(group_cols, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        truth_fail = (d.outcome_truth == "failure").to_numpy().astype(int)
        pred_fail = (d.outcome_pred == "failure").to_numpy().astype(int)
        acc = float((truth_fail == pred_fail).mean())
        succ_recall = float((pred_fail[truth_fail == 0] == 0).mean()) if (truth_fail == 0).any() else float("nan")
        fail_recall = float((pred_fail[truth_fail == 1] == 1).mean()) if (truth_fail == 1).any() else float("nan")
        bal_acc = np.nanmean([succ_recall, fail_recall])
        # failure AUROC from decision-level confidence: p(failure)=conf if pred=fail else 1-conf
        conf = pd.to_numeric(d.confidence, errors="coerce").to_numpy()
        p_fail = np.where(pred_fail == 1, conf, 1 - conf)
        auroc = _auroc(truth_fail.astype(float), p_fail)
        sub = subtype_df
        for col, val in zip(group_cols, keys):
            sub = sub[sub[col] == val]
        macro_f1 = float(np.nanmean(sub.f1.to_numpy())) if len(sub) else float("nan")
        row = dict(zip(group_cols, keys))
        row.update(n_samples=int(len(d)), outcome_accuracy=acc,
                   success_recall=succ_recall, failure_recall=fail_recall,
                   balanced_accuracy=float(bal_acc), failure_auroc=auroc,
                   macro_f1_subtype=macro_f1)
        out.append(row)
    return pd.DataFrame(out).sort_values("balanced_accuracy", ascending=False)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", required=True, type=Path, help="runs/processed/detections_long.csv")
    ap.add_argument("--outdir", type=Path, default=Path("results/direct_stats"))
    ap.add_argument("--task", default=None, help="restrict to a single task")
    ap.add_argument("--by-task", action="store_true",
                    help="split metrics by task as well as model (if the table has a task column)")
    args = ap.parse_args(argv)

    long = pd.read_csv(args.table)
    if args.task and "task" in long.columns:
        long = long[long["task"] == args.task]
    if "status" in long.columns:
        long = long[long["status"].fillna("completed") == "completed"]
    if "outcome_pred" in long.columns:
        long = long[long["outcome_pred"].fillna("") != "ambiguous"]

    group_cols = ["model"]
    if args.by_task and "task" in long.columns:
        group_cols = ["task", "model"]

    subtype_df = per_subtype_stats(long, group_cols)
    outcome_df = per_model_outcome(long, subtype_df, group_cols)

    args.outdir.mkdir(parents=True, exist_ok=True)
    subtype_df.to_csv(args.outdir / "per_subtype_stats.csv", index=False)
    outcome_df.to_csv(args.outdir / "per_model_outcome.csv", index=False)

    lines = [
        "# Direct statistics (model-free)\n",
        f"- Source: `{args.table}`",
        f"- Grouping: {' x '.join(group_cols)}",
        f"- Models: {', '.join(sorted(long['model'].unique()))}",
        f"- Subtypes: {', '.join(sorted(long['subtype'].unique()))}\n",
        "## Per-model outcome metrics\n",
        outcome_df.round(3).to_markdown(index=False),
        "",
        "## Per-subtype recall / precision / F1\n",
        subtype_df.round(3).to_markdown(index=False),
        "",
        "Note: these are hard-0.5 (thresholded-flag) statistics at the benchmark's",
        "own prevalence. For criterion-separated, prevalence-adjustable metrics with",
        "uncertainty, see the SDT-IRT fit (fit_sdt_irt.py).",
    ]
    (args.outdir / "direct_stats.md").write_text("\n".join(lines), encoding="utf-8")
    print(outcome_df.round(3).to_string(index=False))
    print(f"[done] wrote direct statistics to {args.outdir}")


if __name__ == "__main__":
    main()
