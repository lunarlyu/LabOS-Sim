"""Retry full-suite rows that completed without valid confidence scores."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def valid_confidence(row: dict[str, Any]) -> bool:
    prediction = row.get("prediction") or {}
    confidence = prediction.get("confidence")
    return isinstance(confidence, (int, float)) and 0.0 <= float(confidence) <= 1.0


def successful_rows_with_confidence(run_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(run_dir / "predictions.jsonl"):
        if row.get("status") == "completed" and valid_confidence(row):
            rows[row["sample_id"]] = row
    return rows


def consolidated_base_rows(item: dict[str, Any], root: Path) -> dict[str, dict[str, Any]]:
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


def write_retry_config(
    base_config_path: Path,
    retry_config_path: Path,
    sample_ids: set[str],
    attempt: int,
) -> None:
    config = deepcopy(load_json(base_config_path))
    config["name"] = f"{config['name']}_confidence_retry{attempt}"
    config["sample_filter"] = {
        "task_ids": [],
        "include_sample_ids": sorted(sample_ids),
        "exclude_sample_ids": [],
    }
    retry_config_path.parent.mkdir(parents=True, exist_ok=True)
    retry_config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    root = Path.cwd()
    consolidation = load_json(root / "runs" / "retry_consolidation_full_1080p30fps.json")
    retry_root = root / "runs" / "retry_configs"
    report: list[dict[str, Any]] = []

    for item in consolidation["runs"]:
        base_rows = consolidated_base_rows(item, root)
        missing = {
            sample_id
            for sample_id, row in base_rows.items()
            if row.get("status") == "completed" and not valid_confidence(row)
        }
        remaining = set(missing)
        recovered: dict[str, dict[str, Any]] = {}
        retry_runs: list[dict[str, Any]] = []

        for attempt in (1, 2):
            if not remaining:
                break
            retry_config = retry_root / f"{Path(item['base_run']).name}_confidence_retry{attempt}.json"
            retry_run_id = f"{Path(item['base_run']).name}_confidence_retry{attempt}"
            write_retry_config(root / item["base_config"], retry_config, remaining, attempt)
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
            successes = successful_rows_with_confidence(retry_run)
            recovered.update(
                {sample_id: row for sample_id, row in successes.items() if sample_id in remaining}
            )
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

        report.append(
            {
                "label": item["label"],
                "task": item["task"],
                "base_run": item["base_run"],
                "base_config": item["base_config"],
                "initial_missing_confidence": sorted(missing),
                "recovered": sorted(recovered),
                "unresolved": sorted(remaining),
                "retry_runs": retry_runs,
                "retry_cost": sum(run["cost"] for run in retry_runs),
            }
        )

    output = root / "runs" / "confidence_retry_full_1080p30fps.json"
    output.write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "source": "runs/retry_consolidation_full_1080p30fps.json",
                "scope": "completed full 1080px/30fps rows missing valid confidence",
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
        print(
            f"{item['label']}: initial_missing={len(item['initial_missing_confidence'])} "
            f"recovered={len(item['recovered'])} unresolved={len(item['unresolved'])} "
            f"retry_cost={item['retry_cost']:.6f}"
        )


if __name__ == "__main__":
    main()
