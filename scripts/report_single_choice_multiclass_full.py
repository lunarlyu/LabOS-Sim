"""Report the full single-choice multiclass benchmark."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from labos_benchmark.runner import parse_prediction, validate_prediction


RUN_DIR = Path("runs/single_choice_multiclass_full_reasoning512_1080p30fps_001")
REPORT_DIR = Path("reports/single_choice_multiclass_full_reasoning512_1080p30fps")
METADATA_PATH = Path("metadata/real_human_samples_no_multiple.json")
MODEL_ORDER = [
    "minimax/minimax-m3",
    "google/gemini-3.5-flash",
    "google/gemini-3.1-pro-preview-20260219",
    "qwen/qwen3.6-plus",
]
MODEL_LABELS = {
    "minimax/minimax-m3": "MiniMax",
    "google/gemini-3.5-flash": "Gemini Flash",
    "google/gemini-3.1-pro-preview-20260219": "Gemini Pro",
    "qwen/qwen3.6-plus": "Qwen",
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
    "repeated_steps",
    "other_failure",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def usage(row: dict[str, Any]) -> dict[str, Any]:
    path = Path(row.get("response_artifact") or "")
    if not path.exists():
        return {}
    return load_json(path).get("usage") or {}


def cost(row: dict[str, Any]) -> float:
    return float(usage(row).get("cost") or 0.0)


def token_counts(row: dict[str, Any]) -> dict[str, int]:
    row_usage = usage(row)
    completion_details = row_usage.get("completion_tokens_details") or {}
    prompt_details = row_usage.get("prompt_tokens_details") or {}
    completion = int(row_usage.get("completion_tokens") or 0)
    reasoning = int(completion_details.get("reasoning_tokens") or 0)
    return {
        "prompt_tokens": int(row_usage.get("prompt_tokens") or 0),
        "video_tokens": int(prompt_details.get("video_tokens") or 0),
        "completion_tokens": completion,
        "reasoning_tokens": reasoning,
        "visible_completion_tokens_est": max(0, completion - reasoning),
    }


def repair_parse_error(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("status") == "completed" or row.get("prediction") is not None:
        return row
    prediction, parse_error = parse_prediction(row.get("raw_output") or "")
    validation_error = validate_prediction("single_choice_multiclass", prediction)
    if validation_error is not None:
        parse_error = validation_error
        prediction = None
    if prediction is None:
        return row
    repaired = dict(row)
    repaired["status"] = "completed"
    repaired["prediction"] = prediction
    repaired["parse_error"] = None
    repaired["parser_recovered"] = True
    repaired["original_parse_error"] = row.get("parse_error")
    return repaired


def expected_choice_for_sample(sample: dict[str, Any]) -> str:
    if sample.get("is_success"):
        return "success"
    modes = sample.get("failure_modes") or []
    return modes[0] if modes else "other_failure"


def is_exact(row: dict[str, Any]) -> bool:
    return (
        row.get("status") == "completed"
        and (row.get("prediction") or {}).get("choice") == (row.get("expected") or {}).get("choice")
    )


def is_outcome_correct(row: dict[str, Any]) -> bool:
    return (
        row.get("status") == "completed"
        and (row.get("prediction") or {}).get("outcome") == (row.get("expected") or {}).get("outcome")
    )


def collect_rows() -> list[dict[str, Any]]:
    return [repair_parse_error(row) for row in read_jsonl(RUN_DIR / "predictions.jsonl")]


def summarize(rows: list[dict[str, Any]], samples_by_id: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    summaries: list[dict[str, Any]] = []
    category_rows: list[dict[str, Any]] = []
    confusion_rows: list[dict[str, Any]] = []

    rows_by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_model[row["model"]].append(row)

    for model in MODEL_ORDER:
        model_rows = rows_by_model.get(model, [])
        completed = [row for row in model_rows if row.get("status") == "completed"]
        exact = sum(1 for row in model_rows if is_exact(row))
        outcome = sum(1 for row in model_rows if is_outcome_correct(row))
        cost_total = sum(cost(row) for row in model_rows)
        tokens: dict[str, int] = defaultdict(int)
        for row in model_rows:
            for key, value in token_counts(row).items():
                tokens[key] += value
        summaries.append(
            {
                "model": MODEL_LABELS[model],
                "model_id": model,
                "n": len(model_rows),
                "completed": len(completed),
                "parse_errors": len(model_rows) - len(completed),
                "parser_recovered_rows": sum(1 for row in completed if row.get("parser_recovered")),
                "exact_choice_accuracy": exact / len(model_rows) if model_rows else 0.0,
                "outcome_accuracy": outcome / len(model_rows) if model_rows else 0.0,
                "cost": cost_total,
                **tokens,
            }
        )

        for category in CATEGORY_ORDER:
            category_model_rows = [
                row
                for row in model_rows
                if expected_choice_for_sample(samples_by_id[row["sample_id"]]) == category
            ]
            if not category_model_rows:
                continue
            exact_count = sum(1 for row in category_model_rows if is_exact(row))
            outcome_count = sum(1 for row in category_model_rows if is_outcome_correct(row))
            category_rows.append(
                {
                    "model": MODEL_LABELS[model],
                    "model_id": model,
                    "category": category,
                    "n": len(category_model_rows),
                    "exact_recall": exact_count / len(category_model_rows),
                    "outcome_recall": outcome_count / len(category_model_rows),
                    "exact_correct": exact_count,
                    "outcome_correct": outcome_count,
                    "parse_errors": sum(1 for row in category_model_rows if row.get("status") != "completed"),
                }
            )

        for row in model_rows:
            expected = (row.get("expected") or {}).get("choice")
            predicted = (row.get("prediction") or {}).get("choice") if row.get("status") == "completed" else "__parse_error__"
            confusion_rows.append(
                {
                    "model": MODEL_LABELS[model],
                    "model_id": model,
                    "sample_id": row["sample_id"],
                    "expected_choice": expected,
                    "predicted_choice": predicted,
                    "exact_correct": is_exact(row),
                    "outcome_correct": is_outcome_correct(row),
                    "confidence": (row.get("prediction") or {}).get("confidence", ""),
                    "status": row.get("status"),
                    "parse_error": row.get("parse_error") or "",
                    "parser_recovered": bool(row.get("parser_recovered")),
                    "reasoning": (row.get("prediction") or {}).get("reasoning", ""),
                }
            )

    return summaries, category_rows, confusion_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def money(value: float) -> str:
    return f"${value:.6f}"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_markdown(summary: list[dict[str, Any]], category_rows: list[dict[str, Any]]) -> None:
    summary_rows = [
        [
            row["model"],
            row["model_id"],
            f"{row['completed']}/{row['n']}",
            str(row["parse_errors"]),
            str(row["parser_recovered_rows"]),
            pct(row["exact_choice_accuracy"]),
            pct(row["outcome_accuracy"]),
            str(row.get("reasoning_tokens", 0)),
            money(row["cost"]),
        ]
        for row in summary
    ]
    category_table_rows = [
        [
            row["category"],
            row["model"],
            f"{row['exact_correct']}/{row['n']}",
            pct(row["exact_recall"]),
            pct(row["outcome_recall"]),
            str(row["parse_errors"]),
        ]
        for row in sorted(
            category_rows,
            key=lambda item: (CATEGORY_ORDER.index(item["category"]), MODEL_ORDER.index(item["model_id"])),
        )
    ]
    body = f"""# Full Single-Choice Multiclass Benchmark

Updated: {datetime.now(timezone.utc).date().isoformat()}

Run: `{RUN_DIR}`

Config: `configs/benchmarks/single_choice_multiclass_full_reasoning512_1080p30fps.json`

Dataset: `{METADATA_PATH}`, with the 3 `multiple` condition samples removed.

Reasoning setting: `reasoning.max_tokens=512`, `reasoning.exclude=true`.

## Aggregate Results

{md_table(["Model", "Model ID", "Completed", "Parse Errors", "Parser-Recovered", "Exact Choice Acc.", "Outcome Acc.", "Reasoning Tokens", "Cost"], summary_rows)}

## Per-Category Recall

Exact recall means the model selected the exact ground-truth class. Outcome
recall means success-vs-failure was correct for that category.

{md_table(["Category", "Model", "Exact Correct/N", "Exact Recall", "Outcome Recall", "Parse Errors"], category_table_rows)}
"""
    (REPORT_DIR / "summary.md").write_text(body, encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = load_json(METADATA_PATH)
    samples_by_id = {sample["sample_id"]: sample for sample in metadata["samples"]}
    rows = collect_rows()
    summary, category_rows, confusion_rows = summarize(rows, samples_by_id)
    write_csv(REPORT_DIR / "model_summary.csv", summary)
    write_csv(REPORT_DIR / "per_category_recall.csv", category_rows)
    write_csv(REPORT_DIR / "per_sample_predictions.csv", confusion_rows)
    write_markdown(summary, category_rows)
    print(f"Wrote {REPORT_DIR / 'summary.md'}")
    for row in summary:
        print(
            f"{row['model']}: exact={pct(row['exact_choice_accuracy'])} "
            f"outcome={pct(row['outcome_accuracy'])} parse={row['parse_errors']} "
            f"cost={money(row['cost'])}"
        )


if __name__ == "__main__":
    main()
