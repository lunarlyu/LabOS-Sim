"""Generate full-suite comparison tables and SVG charts."""

from __future__ import annotations

import csv
import html
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORT_DIR = Path("reports/full_1080p30fps")
MODEL_ORDER = ["MiniMax", "Gemini Flash", "Gemini Pro", "Qwen"]
MODEL_COLORS = {
    "MiniMax": "#3b82f6",
    "Gemini Flash": "#f59e0b",
    "Gemini Pro": "#10b981",
    "Qwen": "#ef4444",
}
CATEGORY_ORDER = [
    "success",
    "cap_open",
    "tube_drop",
    "tube_empty",
    "vortex_off",
    "wrong_orientation",
    "wrong_rack",
    "rack_flipped",
    "multiple",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{100 * value:.1f}%"


def money(value: float) -> str:
    return f"${value:.6f}"


def model_name(label: str) -> str:
    for suffix in (" binary", " multiclass"):
        if label.endswith(suffix):
            return label.removesuffix(suffix)
    return label


def category_for_sample(sample: dict[str, Any]) -> str:
    if sample.get("is_success"):
        return "success"
    modes = sample.get("failure_modes") or []
    return modes[0] if modes else sample.get("condition_description", "unknown")


def valid_confidence(row: dict[str, Any]) -> bool:
    confidence = (row.get("prediction") or {}).get("confidence")
    return isinstance(confidence, (int, float)) and 0 <= float(confidence) <= 1


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


def exact_target(row: dict[str, Any]) -> bool:
    prediction = row.get("prediction") or {}
    expected = row.get("expected") or {}
    if prediction.get("outcome") != expected.get("outcome"):
        return False
    return sorted(prediction.get("failure_modes") or []) == sorted(
        expected.get("failure_modes") or []
    )


def expected_label_included(row: dict[str, Any]) -> bool:
    prediction = row.get("prediction") or {}
    expected = row.get("expected") or {}
    if expected.get("outcome") == "success":
        return prediction.get("outcome") == "success" and not prediction.get("failure_modes")
    expected_modes = set(expected.get("failure_modes") or [])
    predicted_modes = set(prediction.get("failure_modes") or [])
    return bool(expected_modes & predicted_modes)


def row_cost(row: dict[str, Any]) -> float:
    response_path = Path(row.get("response_artifact") or "")
    if not response_path.exists():
        return 0.0
    response = load_json(response_path)
    return float((response.get("usage") or {}).get("cost") or 0.0)


def total_cost_by_label(root: Path) -> dict[str, float]:
    retry_report = load_json(root / "runs" / "retry_consolidation_full_1080p30fps.json")
    costs = {
        item["label"]: float(item.get("total_cost_with_retries") or 0.0)
        for item in retry_report["runs"]
    }
    confidence_path = root / "runs" / "confidence_retry_full_1080p30fps.json"
    if confidence_path.exists():
        confidence_report = load_json(confidence_path)
        for item in confidence_report.get("runs") or []:
            costs[item["label"]] = costs.get(item["label"], 0.0) + float(
                item.get("retry_cost") or 0.0
            )
    return costs


def consolidated_rows_for_run(item: dict[str, Any], root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        row["sample_id"]: row
        for row in read_jsonl(root / item["base_run"] / "predictions.jsonl")
    }
    recovered = set(item.get("recovered") or [])
    for retry_run in item.get("retry_runs") or []:
        for row in read_jsonl(root / retry_run["run"] / "predictions.jsonl"):
            if row.get("sample_id") in recovered and row.get("status") == "completed":
                rows[row["sample_id"]] = row
    return rows


def confidence_retry_rows(root: Path) -> dict[str, dict[str, dict[str, Any]]]:
    report_path = root / "runs" / "confidence_retry_full_1080p30fps.json"
    if not report_path.exists():
        return {}
    report = load_json(report_path)
    by_run: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for item in report.get("runs") or []:
        recovered = set(item.get("recovered") or [])
        for retry_run in item.get("retry_runs") or []:
            for row in read_jsonl(root / retry_run["run"] / "predictions.jsonl"):
                if row.get("sample_id") in recovered and row.get("status") == "completed":
                    by_run[item["base_run"]][row["sample_id"]] = row
    return dict(by_run)


def final_rows(root: Path) -> list[dict[str, Any]]:
    retry_report = load_json(root / "runs" / "retry_consolidation_full_1080p30fps.json")
    confidence_rows = confidence_retry_rows(root)
    rows: list[dict[str, Any]] = []
    for item in retry_report["runs"]:
        by_sample = consolidated_rows_for_run(item, root)
        by_sample.update(confidence_rows.get(item["base_run"], {}))
        for row in by_sample.values():
            row = dict(row)
            row["_label"] = item["label"]
            row["_model_name"] = model_name(item["label"])
            row["_task"] = item["task"]
            row["_base_run"] = item["base_run"]
            rows.append(row)
    return rows


def summarize_binary(
    rows: list[dict[str, Any]],
    auroc_by_label: dict[str, dict[str, Any]],
    cost_by_label: dict[str, float],
) -> list[dict[str, Any]]:
    out = []
    for model in MODEL_ORDER:
        model_rows = [
            row
            for row in rows
            if row["_model_name"] == model and row["_task"] == "binary_success"
        ]
        tp = tn = fp = fn = correct = completed = parse_errors = 0
        missing_conf = 0
        for row in model_rows:
            if row.get("status") != "completed":
                parse_errors += 1
                continue
            completed += 1
            if not valid_confidence(row):
                missing_conf += 1
            expected = bool((row.get("expected") or {}).get("success"))
            predicted = bool((row.get("prediction") or {}).get("success"))
            correct += int(expected == predicted)
            if expected and predicted:
                tp += 1
            elif not expected and not predicted:
                tn += 1
            elif not expected and predicted:
                fp += 1
            elif expected and not predicted:
                fn += 1
        positives = tp + fn
        negatives = tn + fp
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / positives if positives else None
        specificity = tn / negatives if negatives else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else None
        )
        balanced = (
            (recall + specificity) / 2
            if recall is not None and specificity is not None
            else None
        )
        label = f"{model} binary"
        out.append(
            {
                "model": model,
                "n": len(model_rows),
                "completed": completed,
                "parse_errors": parse_errors,
                "missing_confidence": missing_conf,
                "accuracy": correct / len(model_rows) if model_rows else None,
                "balanced_accuracy": balanced,
                "success_recall": recall,
                "failure_recall": specificity,
                "precision_success": precision,
                "f1_success": f1,
                "tp": tp,
                "tn": tn,
                "fp": fp,
                "fn": fn,
                "auroc": (auroc_by_label.get(label) or {}).get("success_positive_auroc"),
                "cost": cost_by_label.get(label, 0.0),
            }
        )
    return out


def summarize_multiclass(
    rows: list[dict[str, Any]],
    auroc_by_label: dict[str, dict[str, Any]],
    cost_by_label: dict[str, float],
) -> list[dict[str, Any]]:
    out = []
    for model in MODEL_ORDER:
        model_rows = [
            row
            for row in rows
            if row["_model_name"] == model and row["_task"] == "failure_mode_classification"
        ]
        completed = parse_errors = missing_conf = 0
        outcome_correct = exact = included = 0
        for row in model_rows:
            if row.get("status") != "completed":
                parse_errors += 1
                continue
            completed += 1
            if not valid_confidence(row):
                missing_conf += 1
            prediction = row.get("prediction") or {}
            expected = row.get("expected") or {}
            outcome_correct += int(prediction.get("outcome") == expected.get("outcome"))
            exact += int(exact_target(row))
            included += int(expected_label_included(row))
        label = f"{model} multiclass"
        out.append(
            {
                "model": model,
                "n": len(model_rows),
                "completed": completed,
                "parse_errors": parse_errors,
                "missing_confidence": missing_conf,
                "outcome_accuracy": outcome_correct / len(model_rows) if model_rows else None,
                "exact_target_accuracy": exact / len(model_rows) if model_rows else None,
                "expected_label_included_accuracy": included / len(model_rows) if model_rows else None,
                "auroc": (auroc_by_label.get(label) or {}).get("success_positive_auroc"),
                "cost": cost_by_label.get(label, 0.0),
            }
        )
    return out


def summarize_categories(
    rows: list[dict[str, Any]],
    samples_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    binary = []
    multiclass = []
    for model in MODEL_ORDER:
        for category in CATEGORY_ORDER:
            br = [
                row
                for row in rows
                if row["_model_name"] == model
                and row["_task"] == "binary_success"
                and category_for_sample(samples_by_id[row["sample_id"]]) == category
            ]
            if br:
                correct = sum(
                    1
                    for row in br
                    if row.get("status") == "completed"
                    and bool((row.get("expected") or {}).get("success"))
                    == bool((row.get("prediction") or {}).get("success"))
                )
                binary.append(
                    {
                        "model": model,
                        "category": category,
                        "n": len(br),
                        "accuracy": correct / len(br),
                        "correct": correct,
                    }
                )

            mr = [
                row
                for row in rows
                if row["_model_name"] == model
                and row["_task"] == "failure_mode_classification"
                and category_for_sample(samples_by_id[row["sample_id"]]) == category
            ]
            if mr:
                outcome = sum(
                    1
                    for row in mr
                    if row.get("status") == "completed"
                    and (row.get("prediction") or {}).get("outcome")
                    == (row.get("expected") or {}).get("outcome")
                )
                exact = sum(1 for row in mr if row.get("status") == "completed" and exact_target(row))
                included = sum(
                    1
                    for row in mr
                    if row.get("status") == "completed" and expected_label_included(row)
                )
                multiclass.append(
                    {
                        "model": model,
                        "category": category,
                        "n": len(mr),
                        "outcome_accuracy": outcome / len(mr),
                        "exact_target_accuracy": exact / len(mr),
                        "expected_label_included_accuracy": included / len(mr),
                        "outcome_correct": outcome,
                        "exact_correct": exact,
                        "included_correct": included,
                    }
                )
    return binary, multiclass


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def svg_bar_chart(
    path: Path,
    title: str,
    series: dict[str, dict[str, float]],
    y_label: str = "Score",
    max_value: float = 1.0,
    width: int = 1120,
    height: int = 560,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = list(series.keys())
    keys = [key for key in MODEL_ORDER if any(key in values for values in series.values())]
    margin_left = 92
    margin_right = 24
    margin_top = 64
    margin_bottom = 120
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    group_w = plot_w / max(1, len(labels))
    bar_gap = 4
    bar_w = max(5, (group_w - 20) / max(1, len(keys)) - bar_gap)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>text{font-family:Arial,sans-serif;fill:#111827}.muted{fill:#6b7280}.grid{stroke:#e5e7eb}.axis{stroke:#374151}.bar-label{font-size:11px}.tick{font-size:12px}.title{font-size:22px;font-weight:700}.legend{font-size:13px}</style>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{margin_left}" y="34" class="title">{html.escape(title)}</text>',
        f'<text x="22" y="{margin_top + plot_h / 2}" transform="rotate(-90 22 {margin_top + plot_h / 2})" class="muted">{html.escape(y_label)}</text>',
    ]
    for i in range(6):
        value = i / 5 * max_value
        y = margin_top + plot_h - (value / max_value) * plot_h
        parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{margin_left - 10}" y="{y + 4:.1f}" text-anchor="end" class="tick">{100 * value:.0f}%</text>')
    parts.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" class="axis"/>')
    parts.append(f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{width - margin_right}" y2="{margin_top + plot_h}" class="axis"/>')

    for li, label in enumerate(labels):
        base_x = margin_left + li * group_w + 10
        for ki, key in enumerate(keys):
            value = series[label].get(key)
            if value is None:
                continue
            bar_h = max(0, value / max_value * plot_h)
            x = base_x + ki * (bar_w + bar_gap)
            y = margin_top + plot_h - bar_h
            color = MODEL_COLORS.get(key, "#64748b")
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{color}"/>')
            parts.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" text-anchor="middle" class="bar-label">{100 * value:.0f}</text>'
            )
        label_x = margin_left + li * group_w + group_w / 2
        parts.append(
            f'<text x="{label_x:.1f}" y="{margin_top + plot_h + 20}" text-anchor="end" transform="rotate(-35 {label_x:.1f} {margin_top + plot_h + 20})" class="tick">{html.escape(label)}</text>'
        )

    legend_x = margin_left
    legend_y = height - 28
    for i, key in enumerate(keys):
        x = legend_x + i * 150
        parts.append(f'<rect x="{x}" y="{legend_y - 12}" width="14" height="14" fill="{MODEL_COLORS.get(key, "#64748b")}"/>')
        parts.append(f'<text x="{x + 20}" y="{legend_y}" class="legend">{html.escape(key)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def svg_metric_chart(path: Path, title: str, rows: list[dict[str, Any]], metrics: list[str]) -> None:
    series = {
        metric.replace("_", " ").title(): {
            row["model"]: float(row[metric])
            for row in rows
            if row.get(metric) is not None
        }
        for metric in metrics
    }
    svg_bar_chart(path, title, series)


def write_markdown(
    path: Path,
    binary_summary: list[dict[str, Any]],
    multiclass_summary: list[dict[str, Any]],
    binary_categories: list[dict[str, Any]],
    multiclass_categories: list[dict[str, Any]],
    confidence_report: dict[str, Any] | None,
) -> None:
    def md_table(headers: list[str], rows: list[list[str]]) -> str:
        out = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        out.extend("| " + " | ".join(row) + " |" for row in rows)
        return "\n".join(out)

    binary_rows = [
        [
            row["model"],
            pct(row["accuracy"]),
            pct(row["balanced_accuracy"]),
            pct(row["success_recall"]),
            pct(row["failure_recall"]),
            pct(row["precision_success"]),
            pct(row["f1_success"]),
            f"{row['auroc']:.3f}" if row["auroc"] is not None else "n/a",
            str(row["missing_confidence"]),
            money(row["cost"]),
        ]
        for row in binary_summary
    ]
    multiclass_rows = [
        [
            row["model"],
            pct(row["outcome_accuracy"]),
            pct(row["exact_target_accuracy"]),
            pct(row["expected_label_included_accuracy"]),
            f"{row['auroc']:.3f}" if row["auroc"] is not None else "n/a",
            str(row["missing_confidence"]),
            money(row["cost"]),
        ]
        for row in multiclass_summary
    ]

    category_binary_rows = [
        [row["category"], row["model"], f"{row['correct']}/{row['n']}", pct(row["accuracy"])]
        for row in sorted(binary_categories, key=lambda r: (CATEGORY_ORDER.index(r["category"]), MODEL_ORDER.index(r["model"])))
    ]
    category_multi_rows = [
        [
            row["category"],
            row["model"],
            f"{row['outcome_correct']}/{row['n']}",
            pct(row["outcome_accuracy"]),
            pct(row["exact_target_accuracy"]),
            pct(row["expected_label_included_accuracy"]),
        ]
        for row in sorted(multiclass_categories, key=lambda r: (CATEGORY_ORDER.index(r["category"]), MODEL_ORDER.index(r["model"])))
    ]

    confidence_note = ""
    if confidence_report:
        recovered = sum(len(item.get("recovered") or []) for item in confidence_report.get("runs") or [])
        unresolved = sum(len(item.get("unresolved") or []) for item in confidence_report.get("runs") or [])
        cost = sum(float(item.get("retry_cost") or 0) for item in confidence_report.get("runs") or [])
        confidence_note = (
            f"\nSupplemental confidence retries recovered {recovered} rows, left {unresolved} "
            f"rows unresolved, and cost {money(cost)}.\n"
        )

    body = f"""# Full Benchmark Comparison, 1080px/30fps

Updated: {datetime.now(timezone.utc).date().isoformat()}

This report uses the active full-suite runs after failed-row retry consolidation
and merges successful supplemental confidence retries when present. AUROC is
success-positive: `confidence` for predicted-success rows and `1 - confidence`
for predicted-failure rows.{confidence_note}

## Binary Success/Failure

{md_table(["Model", "Accuracy", "Balanced Acc.", "Success Recall", "Failure Recall", "Success Precision", "Success F1", "AUROC", "Missing Conf.", "Cost"], binary_rows)}

## Multiclass Failure Classification

{md_table(["Model", "Outcome Acc.", "Exact Target Acc.", "Expected Label Included", "Success AUROC", "Missing Conf.", "Cost"], multiclass_rows)}

## Binary Per-Category Accuracy

{md_table(["Category", "Model", "Correct/N", "Accuracy"], category_binary_rows)}

## Multiclass Per-Category Metrics

{md_table(["Category", "Model", "Outcome Correct/N", "Outcome Acc.", "Exact Target Acc.", "Expected Label Included"], category_multi_rows)}

## Charts

- `charts/binary_overall_metrics.svg`
- `charts/multiclass_overall_metrics.svg`
- `charts/binary_per_category_accuracy.svg`
- `charts/multiclass_per_category_expected_label.svg`
- `charts/cost_by_model.svg`
"""
    path.write_text(body, encoding="utf-8")


def main() -> None:
    root = Path.cwd()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "charts").mkdir(parents=True, exist_ok=True)

    metadata = load_json(root / "metadata" / "real_human_samples.json")
    samples_by_id = {sample["sample_id"]: sample for sample in metadata["samples"]}
    auroc = load_json(root / "runs" / "auroc_full_1080p30fps.json")
    auroc_by_label = {item["label"]: item for item in auroc["runs"]}
    confidence_path = root / "runs" / "confidence_retry_full_1080p30fps.json"
    confidence_report = load_json(confidence_path) if confidence_path.exists() else None
    cost_by_label = total_cost_by_label(root)

    rows = final_rows(root)
    binary_summary = summarize_binary(rows, auroc_by_label, cost_by_label)
    multiclass_summary = summarize_multiclass(rows, auroc_by_label, cost_by_label)
    binary_categories, multiclass_categories = summarize_categories(rows, samples_by_id)

    write_csv(REPORT_DIR / "binary_model_summary.csv", binary_summary)
    write_csv(REPORT_DIR / "multiclass_model_summary.csv", multiclass_summary)
    write_csv(REPORT_DIR / "binary_per_category_accuracy.csv", binary_categories)
    write_csv(REPORT_DIR / "multiclass_per_category_metrics.csv", multiclass_categories)

    write_markdown(
        REPORT_DIR / "summary.md",
        binary_summary,
        multiclass_summary,
        binary_categories,
        multiclass_categories,
        confidence_report,
    )

    svg_metric_chart(
        REPORT_DIR / "charts" / "binary_overall_metrics.svg",
        "Binary Benchmark: Overall Metrics",
        binary_summary,
        ["accuracy", "balanced_accuracy", "auroc"],
    )
    svg_metric_chart(
        REPORT_DIR / "charts" / "multiclass_overall_metrics.svg",
        "Multiclass Benchmark: Overall Metrics",
        multiclass_summary,
        ["outcome_accuracy", "exact_target_accuracy", "expected_label_included_accuracy", "auroc"],
    )

    binary_category_series: dict[str, dict[str, float]] = defaultdict(dict)
    for row in binary_categories:
        binary_category_series[row["category"]][row["model"]] = row["accuracy"]
    svg_bar_chart(
        REPORT_DIR / "charts" / "binary_per_category_accuracy.svg",
        "Binary Accuracy by Ground-Truth Category",
        dict(binary_category_series),
        width=1320,
        height=640,
    )

    multiclass_category_series: dict[str, dict[str, float]] = defaultdict(dict)
    for row in multiclass_categories:
        multiclass_category_series[row["category"]][row["model"]] = row[
            "expected_label_included_accuracy"
        ]
    svg_bar_chart(
        REPORT_DIR / "charts" / "multiclass_per_category_expected_label.svg",
        "Multiclass Expected Label Included by Ground-Truth Category",
        dict(multiclass_category_series),
        width=1320,
        height=640,
    )

    cost_series = {
        "Binary": {row["model"]: row["cost"] for row in binary_summary},
        "Multiclass": {row["model"]: row["cost"] for row in multiclass_summary},
    }
    max_cost = max(value for values in cost_series.values() for value in values.values())
    svg_bar_chart(
        REPORT_DIR / "charts" / "cost_by_model.svg",
        "OpenRouter Cost by Model and Task",
        cost_series,
        y_label="Cost",
        max_value=max_cost,
    )

    print(f"Wrote {REPORT_DIR / 'summary.md'}")
    print(f"Wrote CSV tables and SVG charts under {REPORT_DIR}")


if __name__ == "__main__":
    main()
