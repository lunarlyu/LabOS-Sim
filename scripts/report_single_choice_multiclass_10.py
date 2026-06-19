"""Report the 10-sample single-choice multiclass benchmark."""

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


BASE_RUN = Path("runs/single_choice_multiclass10_reasoning512_1080p30fps_001")
RETRY_RUNS = [
    Path("runs/single_choice_multiclass10_reasoning512_1080p30fps_minimax_retry1"),
    Path("runs/single_choice_multiclass10_reasoning512_1080p30fps_minimax_retry2"),
]
REPORT_DIR = Path("reports/single_choice_multiclass10_reasoning512_1080p30fps")
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


def is_correct_choice(row: dict[str, Any]) -> bool:
    return (
        row.get("status") == "completed"
        and (row.get("prediction") or {}).get("choice") == (row.get("expected") or {}).get("choice")
    )


def is_correct_outcome(row: dict[str, Any]) -> bool:
    return (
        row.get("status") == "completed"
        and (row.get("prediction") or {}).get("outcome") == (row.get("expected") or {}).get("outcome")
    )


def collect_rows() -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, float], dict[str, dict[str, int]]]:
    rows_by_model_sample: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    cost_by_model: dict[str, float] = defaultdict(float)
    tokens_by_model: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    all_runs = [BASE_RUN] + RETRY_RUNS
    for run in all_runs:
        for row in read_jsonl(run / "predictions.jsonl"):
            row = repair_parse_error(row)
            model = row["model"]
            cost_by_model[model] += cost(row)
            for key, value in token_counts(row).items():
                tokens_by_model[model][key] += value

            current = rows_by_model_sample[model].get(row["sample_id"])
            if current is None:
                rows_by_model_sample[model][row["sample_id"]] = row
            elif current.get("status") != "completed" and row.get("status") == "completed":
                rows_by_model_sample[model][row["sample_id"]] = row

    return rows_by_model_sample, dict(cost_by_model), {k: dict(v) for k, v in tokens_by_model.items()}


def summarize() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows_by_model_sample, cost_by_model, tokens_by_model = collect_rows()
    summary: list[dict[str, Any]] = []
    per_sample: list[dict[str, Any]] = []

    for model in MODEL_ORDER:
        rows = list(rows_by_model_sample.get(model, {}).values())
        completed = [row for row in rows if row.get("status") == "completed"]
        parse_errors = len(rows) - len(completed)
        parser_recovered = sum(1 for row in completed if row.get("parser_recovered"))
        exact = sum(1 for row in rows if is_correct_choice(row))
        outcome = sum(1 for row in rows if is_correct_outcome(row))
        avg_confidence = (
            sum(float((row.get("prediction") or {}).get("confidence") or 0.0) for row in completed)
            / len(completed)
            if completed
            else None
        )
        tokens = tokens_by_model.get(model, {})
        summary.append(
            {
                "model": MODEL_LABELS[model],
                "model_id": model,
                "n": len(rows),
                "completed": len(completed),
                "parse_errors_after_retries": parse_errors,
                "parser_recovered_rows": parser_recovered,
                "exact_choice_accuracy": exact / len(rows) if rows else 0.0,
                "outcome_accuracy": outcome / len(rows) if rows else 0.0,
                "avg_confidence_completed": avg_confidence,
                "cost": cost_by_model.get(model, 0.0),
                "prompt_tokens": tokens.get("prompt_tokens", 0),
                "video_tokens": tokens.get("video_tokens", 0),
                "completion_tokens": tokens.get("completion_tokens", 0),
                "reasoning_tokens": tokens.get("reasoning_tokens", 0),
                "visible_completion_tokens_est": tokens.get("visible_completion_tokens_est", 0),
            }
        )
        for row in sorted(rows, key=lambda item: item["sample_id"]):
            prediction = row.get("prediction") or {}
            per_sample.append(
                {
                    "model": MODEL_LABELS[model],
                    "sample_id": row["sample_id"],
                    "expected_choice": (row.get("expected") or {}).get("choice"),
                    "predicted_choice": prediction.get("choice", ""),
                    "exact_correct": is_correct_choice(row),
                    "outcome_correct": is_correct_outcome(row),
                    "confidence": prediction.get("confidence", ""),
                    "status": row.get("status"),
                    "parse_error": row.get("parse_error") or "",
                    "parser_recovered": bool(row.get("parser_recovered")),
                    "reasoning": prediction.get("reasoning", ""),
                }
            )
    return summary, per_sample


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


def write_markdown(summary: list[dict[str, Any]], per_sample: list[dict[str, Any]]) -> None:
    summary_rows = [
        [
            row["model"],
            row["model_id"],
            f"{row['completed']}/{row['n']}",
            str(row["parse_errors_after_retries"]),
            str(row["parser_recovered_rows"]),
            pct(row["exact_choice_accuracy"]),
            pct(row["outcome_accuracy"]),
            "" if row["avg_confidence_completed"] is None else f"{row['avg_confidence_completed']:.2f}",
            str(row["reasoning_tokens"]),
            money(row["cost"]),
        ]
        for row in summary
    ]
    sample_rows = [
        [
            row["model"],
            row["sample_id"],
            row["expected_choice"],
            row["predicted_choice"],
            "yes" if row["exact_correct"] else "no",
            str(row["confidence"]),
            row["status"],
            "yes" if row["parser_recovered"] else "no",
            str(row["reasoning"]).replace("|", "/"),
        ]
        for row in per_sample
    ]
    body = f"""# Single-Choice Multiclass 10-Sample Benchmark

Updated: {datetime.now(timezone.utc).date().isoformat()}

Run: `runs/single_choice_multiclass10_reasoning512_1080p30fps_001`

MiniMax retries:

- `runs/single_choice_multiclass10_reasoning512_1080p30fps_minimax_retry1`
- `runs/single_choice_multiclass10_reasoning512_1080p30fps_minimax_retry2`

Config: `configs/benchmarks/single_choice_multiclass_10_medium_reasoning_1080p30fps.json`

Dataset: `metadata/real_human_samples_no_multiple.json`, which removes the 3
ambiguous `multiple` condition samples from the benchmark metadata.

Reasoning setting: OpenRouter rejected sending both `reasoning.effort` and
`reasoning.max_tokens`, so the final run used `reasoning.max_tokens=512` with
`reasoning.exclude=true`. This gives a bounded medium-sized thinking budget
while keeping hidden reasoning out of the model output.

## Aggregate Results

{md_table(["Model", "Model ID", "Completed", "Parse Errors", "Parser-Recovered", "Exact Choice Acc.", "Outcome Acc.", "Avg Conf.", "Reasoning Tokens", "Cost"], summary_rows)}

## Per-Sample Predictions

{md_table(["Model", "Sample", "Expected", "Predicted", "Exact?", "Confidence", "Status", "Parser-Recovered", "Reasoning"], sample_rows)}
"""
    (REPORT_DIR / "summary.md").write_text(body, encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary, per_sample = summarize()
    write_csv(REPORT_DIR / "model_summary.csv", summary)
    write_csv(REPORT_DIR / "per_sample_predictions.csv", per_sample)
    write_markdown(summary, per_sample)
    print(f"Wrote {REPORT_DIR / 'summary.md'}")
    for row in summary:
        print(
            f"{row['model']}: exact={pct(row['exact_choice_accuracy'])} "
            f"outcome={pct(row['outcome_accuracy'])} parse={row['parse_errors_after_retries']} "
            f"cost={money(row['cost'])}"
        )


if __name__ == "__main__":
    main()
