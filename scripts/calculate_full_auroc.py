"""Calculate AUROC for the active full 1080px/30fps benchmark suite."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def auc_rank(labels: list[int], scores: list[float]) -> float | None:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None

    ordered = sorted(enumerate(scores), key=lambda item: item[1])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        average_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[ordered[k][0]] = average_rank
        i = j

    positive_rank_sum = sum(rank for rank, label in zip(ranks, labels) if label == 1)
    return (positive_rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def success_label(row: dict[str, Any]) -> int:
    expected = row.get("expected") or {}
    if "success" in expected:
        return 1 if expected.get("success") else 0
    return 1 if expected.get("outcome") == "success" else 0


def predicted_success(row: dict[str, Any]) -> bool:
    prediction = row.get("prediction") or {}
    if "success" in prediction:
        return bool(prediction.get("success"))
    return prediction.get("outcome") == "success"


def success_score(row: dict[str, Any]) -> float | None:
    prediction = row.get("prediction") or {}
    confidence = prediction.get("confidence")
    if not isinstance(confidence, (int, float)):
        return None
    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        return None
    return confidence if predicted_success(row) else 1.0 - confidence


def consolidated_rows(item: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    base_rows = {
        row["sample_id"]: row
        for row in read_jsonl(root / item["base_run"] / "predictions.jsonl")
    }
    recovered = set(item.get("recovered") or [])
    if not recovered:
        return list(base_rows.values())

    for retry_run in item.get("retry_runs") or []:
        for row in read_jsonl(root / retry_run["run"] / "predictions.jsonl"):
            if row.get("sample_id") in recovered and row.get("status") == "completed":
                base_rows[row["sample_id"]] = row
    return list(base_rows.values())


def confidence_retry_rows(root: Path) -> dict[str, dict[str, dict[str, Any]]]:
    report_path = root / "runs" / "confidence_retry_full_1080p30fps.json"
    if not report_path.exists():
        return {}

    report = load_json(report_path)
    rows_by_run: dict[str, dict[str, dict[str, Any]]] = {}
    for item in report.get("runs") or []:
        recovered = set(item.get("recovered") or [])
        if not recovered:
            continue
        rows_by_run.setdefault(item["base_run"], {})
        for retry_run in item.get("retry_runs") or []:
            for row in read_jsonl(root / retry_run["run"] / "predictions.jsonl"):
                if row.get("sample_id") in recovered and row.get("status") == "completed":
                    rows_by_run[item["base_run"]][row["sample_id"]] = row
    return rows_by_run


def summarize_item(item: dict[str, Any], root: Path) -> dict[str, Any]:
    rows_by_sample = {row["sample_id"]: row for row in consolidated_rows(item, root)}
    rows_by_sample.update(confidence_retry_rows(root).get(item["base_run"], {}))
    rows = list(rows_by_sample.values())
    scored_rows = []
    missing_confidence = 0
    for row in rows:
        if row.get("status") != "completed":
            continue
        score = success_score(row)
        if score is None:
            missing_confidence += 1
            continue
        scored_rows.append((success_label(row), score))

    labels = [label for label, _ in scored_rows]
    scores = [score for _, score in scored_rows]
    positives = sum(labels)
    negatives = len(labels) - positives
    return {
        "label": item["label"],
        "task": item["task"],
        "base_run": item["base_run"],
        "scored_rows": len(scored_rows),
        "missing_or_invalid_confidence": missing_confidence,
        "positives": positives,
        "negatives": negatives,
        "success_positive_auroc": auc_rank(labels, scores),
    }


def main() -> None:
    root = Path.cwd()
    consolidation_path = root / "runs" / "retry_consolidation_full_1080p30fps.json"
    consolidation = load_json(consolidation_path)
    confidence_retry_path = root / "runs" / "confidence_retry_full_1080p30fps.json"
    summaries = [summarize_item(item, root) for item in consolidation["runs"]]

    output = root / "runs" / "auroc_full_1080p30fps.json"
    output.write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "source": str(consolidation_path.relative_to(root)),
                "confidence_retry_source": (
                    str(confidence_retry_path.relative_to(root))
                    if confidence_retry_path.exists()
                    else None
                ),
                "score_definition": (
                    "success-positive score = confidence when the model predicts success, "
                    "and 1 - confidence when the model predicts failure"
                ),
                "runs": summaries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {output}")
    print(
        "| Model | Task | Scored rows | Positives | Negatives | Missing confidence | Success-positive AUROC |"
    )
    print("|---|---|---:|---:|---:|---:|---:|")
    for summary in summaries:
        auc = summary["success_positive_auroc"]
        auc_text = "n/a" if auc is None else f"{auc:.3f}"
        print(
            f"| {summary['label']} | {summary['task']} | {summary['scored_rows']} | "
            f"{summary['positives']} | {summary['negatives']} | "
            f"{summary['missing_or_invalid_confidence']} | {auc_text} |"
        )


if __name__ == "__main__":
    main()
