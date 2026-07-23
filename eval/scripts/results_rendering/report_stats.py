#!/usr/bin/env python3
"""Direct (non-Bayesian) statistics from the flag table.

Reads eval/runs/processed/detections_long.csv and reports, per model (optionally
split by task), the headline classification metrics — a model-free complement to the
SDT-IRT fit (fit_sdt_irt.py). These are the "report direct statistics from the
table" deliverable.

Outputs (to --outdir, default eval/results/direct_stats):
  per_model_metrics.csv   P1 binary metrics or P2/P3 exact primary-type metrics
  per_subtype_stats.csv   per type: exact overall accuracy, precision, recall, F1, FPR
  direct_stats.md         human-readable summary
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

EVAL_ROOT = Path(__file__).resolve().parents[2]


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
    """Eight-class per-type metrics (success + seven failure types)."""
    out = []
    for keys, d in long.groupby(group_cols, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        if "task" in group_cols:
            task_value = str(keys[group_cols.index("task")])
            if task_value.endswith("closed_binary"):
                continue
        samples = d.drop_duplicates("sample_id")
        exact_accuracy = float((samples["truth_type"] == samples["pred_type"]).mean())
        # Fixed benchmark universe: success + the seven catalog error types.
        # `other_failure`/unclassified predictions count as exact-match errors
        # but never become a ninth scored class.
        classes = ["success", "cap_open", "tube_drop", "tube_empty", "vortex_off",
                   "wrong_orientation", "wrong_rack", "rack_flipped"]
        for class_name in classes:
            truth = samples["truth_type"] == class_name
            pred = samples["pred_type"] == class_name
            tp = int((truth & pred).sum())
            fp = int((~truth & pred).sum())
            fn = int((truth & ~pred).sum())
            tn = int((~truth & ~pred).sum())
            recall, precision, f1 = _prf(tp, fp, fn)
            row = dict(zip(group_cols, keys))
            row.update(type=class_name, n_truth=tp + fn,
                       overall_exact_accuracy=exact_accuracy,
                       precision=precision, recall=recall, f1=f1,
                       fpr=(fp / (fp + tn) if (fp + tn) else float("nan")))
            out.append(row)
    return pd.DataFrame(out)


def per_model_metrics(long: pd.DataFrame, subtype_df: pd.DataFrame,
                      group_cols: list[str]) -> pd.DataFrame:
    """Headline task metric: P1 binary outcome; P2/P3 primary failure type."""
    one = long.drop_duplicates(subset=group_cols + ["sample_id"]).copy()
    out = []
    for keys, d in one.groupby(group_cols, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        tasks = set(d["task"].dropna().astype(str)) if "task" in d.columns else set()
        is_binary = bool(tasks) and all(t.endswith("closed_binary") for t in tasks)
        sub = subtype_df
        for col, val in zip(group_cols, keys):
            sub = sub[sub[col] == val]
        if is_binary:
            # P1 positive class is correct/success, per benchmark convention.
            truth = (d.outcome_truth == "success").astype(int)
            pred = (d.outcome_pred == "success").astype(int)
            tp = int(((truth == 1) & (pred == 1)).sum())
            fp = int(((truth == 0) & (pred == 1)).sum())
            fn = int(((truth == 1) & (pred == 0)).sum())
            tn = int(((truth == 0) & (pred == 0)).sum())
            recall, precision, f1 = _prf(tp, fp, fn)
            failure_recall = tn / (tn + fp) if (tn + fp) else float("nan")
            row_metrics = {
                "metric_target": "binary_correctness",
                "n_samples": len(d),
                "accuracy": float((truth == pred).mean()),
                "balanced_accuracy": float(np.nanmean([recall, failure_recall])),
                "success_recall": recall,
                "failure_recall": failure_recall,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "fpr": fp / (fp + tn) if (fp + tn) else float("nan"),
            }
        else:
            row_metrics = {
                "metric_target": "eight_class_primary_type",
                "n_samples": len(d),
                "accuracy": float((d["truth_type"] == d["pred_type"]).mean()),
                "balanced_accuracy": float("nan"),
                "success_recall": float("nan"),
                "failure_recall": float("nan"),
                "precision": float(np.nanmean(sub["precision"])) if len(sub) else float("nan"),
                "recall": float(np.nanmean(sub["recall"])) if len(sub) else float("nan"),
                "f1": float(np.nanmean(sub["f1"])) if len(sub) else float("nan"),
                "fpr": float(np.nanmean(sub["fpr"])) if len(sub) else float("nan"),
            }
        row = dict(zip(group_cols, keys))
        row.update(row_metrics)
        out.append(row)
    return pd.DataFrame(out).sort_values("accuracy", ascending=False)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", required=True, type=Path, help="runs/processed/detections_long.csv")
    ap.add_argument("--outdir", type=Path, default=EVAL_ROOT / "results/direct_stats")
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
    outcome_df = per_model_metrics(long, subtype_df, group_cols)

    args.outdir.mkdir(parents=True, exist_ok=True)
    subtype_df.to_csv(args.outdir / "per_subtype_stats.csv", index=False)
    outcome_df.to_csv(args.outdir / "per_model_metrics.csv", index=False)

    lines = [
        "# Direct statistics (model-free)\n",
        f"- Source: `{args.table}`",
        f"- Grouping: {' x '.join(group_cols)}",
        f"- Models: {', '.join(sorted(long['model'].unique()))}",
        f"- Subtypes: {', '.join(sorted(long['subtype'].unique()))}\n",
        "## Complete headline metrics\n",
        outcome_df.round(3).to_markdown(index=False),
        "",
        "## Per-type precision / recall / F1 / FPR\n",
        subtype_df.round(3).to_markdown(index=False),
        "",
        "For P1, the metric target is binary correctness (success/correct is positive).",
        "For P2/P3, the target is one of eight classes: success or seven error types.",
        "`accuracy` requires the single primary predicted type to exactly equal truth.",
        "If a model returns multiple ordered types, only its first (most important)",
        "type is scored. Precision/recall/F1/FPR are macro per-type for P2/P3.",
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
