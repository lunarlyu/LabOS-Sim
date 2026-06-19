"""Generate recovery configs for the interrupted full single-choice run."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


BASE_CONFIG = Path("configs/benchmarks/single_choice_multiclass_full_reasoning512_1080p30fps.json")
BASE_RUN = Path("runs/single_choice_multiclass_full_reasoning512_1080p30fps_001")
METADATA_PATH = Path("metadata/real_human_samples_no_multiple.json")
OUT_DIR = Path("configs/benchmarks/recovery")

MODELS = [
    "minimax/minimax-m3",
    "google/gemini-3.5-flash",
    "google/gemini-3.1-pro-preview-20260219",
    "qwen/qwen3.6-plus",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_config(name: str, model: str, sample_ids: list[str]) -> Path:
    config = deepcopy(json.loads(BASE_CONFIG.read_text(encoding="utf-8")))
    config["name"] = name
    config["models"] = [model]
    config["sample_filter"] = {
        "task_ids": [],
        "include_sample_ids": sample_ids,
        "exclude_sample_ids": [],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    all_sample_ids = [sample["sample_id"] for sample in metadata["samples"]]
    predictions = read_jsonl(BASE_RUN / "predictions.jsonl")
    errors = read_jsonl(BASE_RUN / "errors.jsonl")

    predictions_by_model: dict[str, dict[str, dict[str, Any]]] = {model: {} for model in MODELS}
    for row in predictions:
        predictions_by_model.setdefault(row["model"], {})[row["sample_id"]] = row

    errors_by_model: dict[str, set[str]] = {model: set() for model in MODELS}
    for row in errors:
        errors_by_model.setdefault(row.get("model", ""), set()).add(row["sample_id"])

    targets = []

    qwen_missing = [
        sample_id
        for sample_id in all_sample_ids
        if sample_id not in predictions_by_model.get("qwen/qwen3.6-plus", {})
    ]
    targets.append(
        (
            "single_choice_multiclass_full_reasoning512_1080p30fps_qwen_missing",
            "qwen/qwen3.6-plus",
            qwen_missing,
        )
    )

    gemini_pro_seen = set(predictions_by_model.get("google/gemini-3.1-pro-preview-20260219", {}))
    gemini_pro_missing_or_error = [
        sample_id
        for sample_id in all_sample_ids
        if sample_id not in gemini_pro_seen
        or sample_id in errors_by_model.get("google/gemini-3.1-pro-preview-20260219", set())
    ]
    targets.append(
        (
            "single_choice_multiclass_full_reasoning512_1080p30fps_gemini_pro_missing_errors",
            "google/gemini-3.1-pro-preview-20260219",
            gemini_pro_missing_or_error,
        )
    )

    for model, prefix in [
        ("minimax/minimax-m3", "minimax_parse_errors"),
        ("google/gemini-3.1-pro-preview-20260219", "gemini_pro_parse_errors"),
    ]:
        parse_error_ids = [
            row["sample_id"]
            for row in predictions_by_model.get(model, {}).values()
            if row.get("status") != "completed"
        ]
        targets.append(
            (
                f"single_choice_multiclass_full_reasoning512_1080p30fps_{prefix}",
                model,
                parse_error_ids,
            )
        )

    for name, model, sample_ids in targets:
        path = write_config(name, model, sample_ids)
        print(f"{path}: model={model} samples={len(sample_ids)}")


if __name__ == "__main__":
    main()
