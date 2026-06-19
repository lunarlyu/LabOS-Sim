from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Any


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    if not y_true:
        return 0.0
    return sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true)


def per_category_recall(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    totals = Counter(y_true)
    correct = Counter(t for t, p in zip(y_true, y_pred) if t == p)
    return {label: correct[label] / totals[label] for label in sorted(totals)}


def balanced_accuracy(y_true: list[str], y_pred: list[str]) -> float:
    recalls = per_category_recall(y_true, y_pred)
    return sum(recalls.values()) / len(recalls) if recalls else 0.0


def macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    labels = sorted(set(y_true) | set(y_pred))
    if not labels:
        return 0.0
    scores = []
    for label in labels:
        tp = sum(t == label and p == label for t, p in zip(y_true, y_pred))
        fp = sum(t != label and p == label for t, p in zip(y_true, y_pred))
        fn = sum(t == label and p != label for t, p in zip(y_true, y_pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return sum(scores) / len(scores)


def bootstrap_ci(
    y_true: list[str],
    y_pred: list[str],
    metric_name: str = "accuracy",
    *,
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 0,
) -> dict[str, Any]:
    if not y_true:
        return {"metric": metric_name, "low": 0.0, "high": 0.0}
    metric_fn = {
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "macro_f1": macro_f1,
    }[metric_name]
    rng = random.Random(seed)
    values = []
    n = len(y_true)
    for _ in range(n_resamples):
        indices = [rng.randrange(n) for _ in range(n)]
        values.append(metric_fn([y_true[i] for i in indices], [y_pred[i] for i in indices]))
    values.sort()
    alpha = 1 - confidence_level
    low = values[int(alpha / 2 * (n_resamples - 1))]
    high = values[int((1 - alpha / 2) * (n_resamples - 1))]
    return {"metric": metric_name, "low": low, "high": high}


def compute_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    return {
        "accuracy": accuracy(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy(y_true, y_pred),
        "macro_f1": macro_f1(y_true, y_pred),
        "per_category_recall": per_category_recall(y_true, y_pred),
    }
