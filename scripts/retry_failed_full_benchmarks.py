"""Retry failed rows from the active full 1080p/30fps benchmark suite."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE_FULL_RUNS = [
    {
        "label": "MiniMax binary",
        "task": "binary_success",
        "config": "configs/benchmarks/binary_full_minimax_1080p30fps.json",
        "run": "runs/binary_full_minimax_1080p30fps_001",
    },
    {
        "label": "Gemini Flash binary",
        "task": "binary_success",
        "config": "configs/benchmarks/binary_full_gemini_flash_1080p30fps.json",
        "run": "runs/binary_full_gemini_flash_1080p30fps_001",
    },
    {
        "label": "Gemini Pro binary",
        "task": "binary_success",
        "config": "configs/benchmarks/binary_full_gemini_pro_1080p30fps.json",
        "run": "runs/binary_full_gemini_pro_1080p30fps_001",
    },
    {
        "label": "Qwen binary",
        "task": "binary_success",
        "config": "configs/benchmarks/binary_full_qwen_1080p30fps.json",
        "run": "runs/binary_full_qwen_1080p30fps_001",
    },
    {
        "label": "Gemini Flash multiclass",
        "task": "failure_mode_classification",
        "config": "configs/benchmarks/multiclass_full_gemini_flash_1080p30fps.json",
        "run": "runs/multiclass_full_gemini_flash_1080p30fps_001",
    },
    {
        "label": "Gemini Pro multiclass",
        "task": "failure_mode_classification",
        "config": "configs/benchmarks/multiclass_full_gemini_pro_1080p30fps.json",
        "run": "runs/multiclass_full_gemini_pro_1080p30fps_001",
    },
    {
        "label": "MiniMax multiclass",
        "task": "failure_mode_classification",
        "config": "configs/benchmarks/multiclass_full_minimax_1080p30fps.json",
        "run": "runs/multiclass_full_minimax_1080p30fps_001",
    },
    {
        "label": "Qwen multiclass",
        "task": "failure_mode_classification",
        "config": "configs/benchmarks/multiclass_full_qwen_1080p30fps.json",
        "run": "runs/multiclass_full_qwen_1080p30fps_001",
    },
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


def usage_cost(row: dict[str, Any]) -> float:
    response_path = Path(row.get("response_artifact") or "")
    if not response_path.exists():
        return 0.0
    response = load_json(response_path)
    return float((response.get("usage") or {}).get("cost") or 0.0)


def run_cost(run_dir: Path) -> float:
    return sum(usage_cost(row) for row in read_jsonl(run_dir / "predictions.jsonl"))


def failed_sample_ids(run_dir: Path) -> set[str]:
    failed: set[str] = set()
    for row in read_jsonl(run_dir / "predictions.jsonl"):
        if row.get("status") != "completed":
            failed.add(row["sample_id"])
    for row in read_jsonl(run_dir / "errors.jsonl"):
        failed.add(row["sample_id"])
    return failed


def successful_retry_rows(run_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(run_dir / "predictions.jsonl"):
        if row.get("status") == "completed":
            rows[row["sample_id"]] = row
    return rows


def write_retry_config(base_config_path: Path, retry_config_path: Path, sample_ids: set[str], attempt: int) -> None:
    config = deepcopy(load_json(base_config_path))
    config["name"] = f"{config['name']}_retry{attempt}"
    config["sample_filter"] = {
        "task_ids": [],
        "include_sample_ids": sorted(sample_ids),
        "exclude_sample_ids": [],
    }
    retry_config_path.parent.mkdir(parents=True, exist_ok=True)
    retry_config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def expected_mode_included(row: dict[str, Any]) -> bool:
    prediction = row.get("prediction") or {}
    expected = row.get("expected") or {}
    if expected.get("outcome") == "success":
        return prediction.get("outcome") == "success" and not prediction.get("failure_modes")
    expected_modes = set(expected.get("failure_modes") or [])
    predicted_modes = set(prediction.get("failure_modes") or [])
    return bool(expected_modes & predicted_modes)


def exact_target(row: dict[str, Any]) -> bool:
    prediction = row.get("prediction") or {}
    expected = row.get("expected") or {}
    if prediction.get("outcome") != expected.get("outcome"):
        return False
    return sorted(prediction.get("failure_modes") or []) == sorted(expected.get("failure_modes") or [])


def compute_metrics(task: str, rows: list[dict[str, Any]], planned: int) -> dict[str, Any]:
    parse_errors = sum(1 for row in rows if row.get("status") != "completed")
    if task == "binary_success":
        tp = tn = fp = fn = correct = 0
        for row in rows:
            prediction = row.get("prediction")
            if not prediction:
                continue
            expected = bool(row["expected"]["success"])
            predicted = bool(prediction.get("success"))
            if expected == predicted:
                correct += 1
            if expected and predicted:
                tp += 1
            elif not expected and not predicted:
                tn += 1
            elif not expected and predicted:
                fp += 1
            elif expected and not predicted:
                fn += 1
        return {
            "parse_errors": parse_errors,
            "correct": correct,
            "planned": planned,
            "accuracy": correct / planned if planned else 0,
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
        }
    outcome_correct = exact = included = 0
    for row in rows:
        prediction = row.get("prediction")
        if not prediction:
            continue
        if prediction.get("outcome") == (row.get("expected") or {}).get("outcome"):
            outcome_correct += 1
        if exact_target(row):
            exact += 1
        if expected_mode_included(row):
            included += 1
    return {
        "parse_errors": parse_errors,
        "outcome_correct": outcome_correct,
        "planned": planned,
        "outcome_accuracy": outcome_correct / planned if planned else 0,
        "exact_target": exact,
        "exact_target_accuracy": exact / planned if planned else 0,
        "expected_label_included": included,
        "expected_label_included_accuracy": included / planned if planned else 0,
    }


def main() -> None:
    root = Path.cwd()
    retry_root = root / "runs" / "retry_configs"
    report: list[dict[str, Any]] = []

    for item in ACTIVE_FULL_RUNS:
        base_run = root / item["run"]
        state = load_json(base_run / "state.json")
        base_predictions = read_jsonl(base_run / "predictions.jsonl")
        failures = failed_sample_ids(base_run)
        recovered: dict[str, dict[str, Any]] = {}
        retry_runs: list[dict[str, Any]] = []

        remaining = set(failures)
        for attempt in (1, 2):
            if not remaining:
                break
            retry_config = retry_root / f"{Path(item['run']).name}_retry{attempt}.json"
            retry_run_id = f"{Path(item['run']).name}_retry{attempt}"
            write_retry_config(root / item["config"], retry_config, remaining, attempt)
            subprocess.run(
                [
                    sys.executable,
                    "scripts/run_benchmark.py",
                    "--config",
                    str(retry_config),
                    "--run-id",
                    retry_run_id,
                    "--force",
                ],
                check=True,
            )
            retry_run = root / "runs" / retry_run_id
            successes = successful_retry_rows(retry_run)
            recovered.update({sample_id: row for sample_id, row in successes.items() if sample_id in remaining})
            remaining = remaining - set(successes)
            retry_runs.append(
                {
                    "attempt": attempt,
                    "run": str(Path("runs") / retry_run_id),
                    "attempted": len(read_jsonl(retry_run / "predictions.jsonl"))
                    + len(read_jsonl(retry_run / "errors.jsonl")),
                    "recovered": len(successes),
                    "cost": run_cost(retry_run),
                    "remaining_after_attempt": sorted(remaining),
                }
            )

        consolidated_by_sample = {row["sample_id"]: row for row in base_predictions}
        for sample_id, row in recovered.items():
            consolidated_by_sample[sample_id] = row
        consolidated_rows = list(consolidated_by_sample.values())
        retry_cost = sum(run["cost"] for run in retry_runs)
        report.append(
            {
                "label": item["label"],
                "task": item["task"],
                "base_run": item["run"],
                "base_config": item["config"],
                "planned": state["planned"],
                "initial_failures": sorted(failures),
                "recovered": sorted(recovered),
                "unresolved": sorted(remaining),
                "base_cost": run_cost(base_run),
                "retry_cost": retry_cost,
                "total_cost_with_retries": run_cost(base_run) + retry_cost,
                "retry_runs": retry_runs,
                "consolidated_metrics": compute_metrics(
                    item["task"],
                    consolidated_rows,
                    int(state["planned"]),
                ),
            }
        )

    output = root / "runs" / "retry_consolidation_full_1080p30fps.json"
    output.write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "scope": "active full 1080px/30fps binary and multiclass benchmarks",
                "max_retries": 2,
                "runs": report,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output}")
    for item in report:
        metrics = item["consolidated_metrics"]
        print(
            f"{item['label']}: initial_failures={len(item['initial_failures'])} "
            f"recovered={len(item['recovered'])} unresolved={len(item['unresolved'])} "
            f"retry_cost={item['retry_cost']:.6f} metrics={metrics}"
        )


if __name__ == "__main__":
    main()
