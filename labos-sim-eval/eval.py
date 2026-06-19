from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from adapters.labos_vlm import get_adapter
from dataset import filter_samples, load_samples, resolve_sample_media
from metrics import compute_metrics
from prompts_loader import load_prompt, load_prompt_with_protocol
from run_metadata import write_run_metadata


def load_config(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def run_dir_for(config: dict[str, Any]) -> Path:
    run = config.get("run") or {}
    name = run.get("name") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(run.get("output_dir", "results")) / name


def expected_for_prompt(prompt_id: str, expected_choice: str) -> str:
    if prompt_id == "p1_closed_binary":
        return "yes" if expected_choice == "success" else "no"
    if prompt_id == "p2_open_detection":
        return "no_error" if expected_choice == "success" else "error"
    return expected_choice


def dry_prediction(prompt_id: str, expected_choice: str) -> str:
    # Deterministic placeholder until adapters are wired.
    return expected_for_prompt(prompt_id, expected_choice)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LabOS-Sim evaluation.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    dry_run = args.dry_run or bool((config.get("run") or {}).get("dry_run", False))
    output_dir = run_dir_for(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "api_logs").mkdir(exist_ok=True)

    logging.basicConfig(
        filename=output_dir / "errors.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    shutil.copyfile(args.config, output_dir / "config_snapshot.yaml")
    write_run_metadata(output_dir / "run_metadata.json", config)

    dataset_config = config["dataset"]
    samples = load_samples(dataset_config["metadata_path"])
    samples = filter_samples(
        samples,
        exclude_condition_folders=set(dataset_config.get("exclude_condition_folders") or []),
        max_samples=dataset_config.get("max_samples"),
    )

    prompt_root = (config.get("prompts") or {}).get("root", "prompts")
    active_prompts = (config.get("prompts") or {}).get("active", [])
    protocol_file = (config.get("prompts") or {}).get("protocol_file", "vortex_protocol.txt")

    predictions: list[dict[str, Any]] = []
    for model in config.get("models") or []:
        if model.get("enabled") is False:
            continue
        for prompt_id in active_prompts:
            if prompt_id == "p5_protocol_grounded":
                prompt_text = load_prompt_with_protocol(prompt_root, prompt_id, protocol_file)
            else:
                prompt_text = load_prompt(prompt_root, prompt_id)
            for sample in samples:
                expected = expected_for_prompt(prompt_id, sample.expected_choice)
                if dry_run:
                    predicted = dry_prediction(prompt_id, sample.expected_choice)
                    raw_output = json.dumps({"dry_run": True, "prediction": predicted})
                    finish_reason = None
                    latency_s = None
                    usage_json = "{}"
                else:
                    input_mode = model.get("input_mode") or (config.get("media") or {}).get("input_mode", "video")
                    media = resolve_sample_media(
                        sample,
                        data_root=dataset_config["data_root"],
                        camera_views=(config.get("media") or {}).get("camera_views") or [],
                        max_videos=int((config.get("media") or {}).get("max_videos_per_sample") or 0),
                        input_mode=input_mode,
                    )
                    adapter = get_adapter(model["adapter"], model)
                    result = adapter.generate(
                        prompt=prompt_text,
                        media=media,
                        request_metadata={
                            "sample_id": sample.sample_id,
                            "prompt_id": prompt_id,
                            "model_name": model["name"],
                            "input_mode": input_mode,
                        },
                    )
                    predicted = result.parsed.get("prediction") if result.parsed else ""
                    raw_output = result.raw_text
                    finish_reason = result.finish_reason
                    latency_s = result.latency_s
                    usage_json = json.dumps(result.usage)
                predictions.append(
                    {
                        "model": model["name"],
                        "adapter": model["adapter"],
                        "model_id": model.get("model_id"),
                        "provider_model_id": model.get("provider_model_id"),
                        "prompt_id": prompt_id,
                        "sample_id": sample.sample_id,
                        "expected": expected,
                        "prediction": predicted,
                        "raw_output": raw_output,
                        "finish_reason": finish_reason,
                        "latency_s": latency_s,
                        "usage_json": usage_json,
                        "prompt_chars": len(prompt_text),
                    }
                )

    write_csv(output_dir / "predictions.csv", predictions)

    metrics_rows: list[dict[str, Any]] = []
    for model_name in sorted({row["model"] for row in predictions}):
        for prompt_id in sorted({row["prompt_id"] for row in predictions}):
            rows = [
                row
                for row in predictions
                if row["model"] == model_name and row["prompt_id"] == prompt_id
            ]
            metric = compute_metrics(
                [row["expected"] for row in rows],
                [row["prediction"] for row in rows],
            )
            metrics_rows.append(
                {
                    "model": model_name,
                    "prompt_id": prompt_id,
                    "accuracy": metric["accuracy"],
                    "balanced_accuracy": metric["balanced_accuracy"],
                    "macro_f1": metric["macro_f1"],
                    "per_category_recall_json": json.dumps(metric["per_category_recall"]),
                }
            )
    write_csv(output_dir / "metrics.csv", metrics_rows)
    print(f"Wrote {output_dir}")


if __name__ == "__main__":
    main()
