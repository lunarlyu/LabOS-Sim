from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset import BenchmarkSample, filter_samples, load_samples, select_videos
from .io_utils import append_jsonl, atomic_write_json, read_json, safe_name
from .media import maybe_transcode_videos
from .openrouter import (
    OpenRouterClient,
    build_messages,
    build_response_format,
    extract_content,
    redact_payload,
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_prompt(task_name: str) -> str:
    prompt_map = {
        "binary_success": Path("prompts") / "vortexing_binary_success.md",
        "failure_mode_classification": Path("prompts")
        / "vortexing_failure_mode_classification.md",
        "single_choice_multiclass": Path("prompts") / "vortexing_single_choice_multiclass.md",
    }
    return prompt_map[task_name].read_text(encoding="utf-8")


def parse_prediction(content: str) -> tuple[dict[str, Any] | None, str | None]:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if not stripped:
        return None, "model response was empty"
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        first_json_start = stripped.find("{")
        if first_json_start < 0:
            return None, str(exc)
        decoder = json.JSONDecoder()
        try:
            parsed, _ = decoder.raw_decode(stripped[first_json_start:])
        except json.JSONDecodeError:
            return None, str(exc)
    if not isinstance(parsed, dict):
        return None, "model response JSON was not an object"
    return parsed, None


def validate_prediction(task_name: str, prediction: dict[str, Any] | None) -> str | None:
    if prediction is None:
        return None
    confidence = prediction.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return "model response missing numeric confidence"
    if not 0 <= float(confidence) <= 1:
        return "model response confidence outside [0, 1]"
    if task_name == "binary_success":
        if not isinstance(prediction.get("success"), bool):
            return "binary response missing boolean success"
    elif task_name == "failure_mode_classification":
        if prediction.get("outcome") not in {"success", "failure"}:
            return "classification response missing valid outcome"
        if not isinstance(prediction.get("failure_modes"), list):
            return "classification response missing failure_modes list"
    elif task_name == "single_choice_multiclass":
        valid_choices = {
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
        }
        choice = prediction.get("choice")
        if choice not in valid_choices:
            return "single-choice response missing valid choice"
        if prediction.get("outcome") not in {"success", "failure"}:
            return "single-choice response missing valid outcome"
        failure_modes = prediction.get("failure_modes")
        if not isinstance(failure_modes, list):
            return "single-choice response missing failure_modes list"
        if choice == "success":
            if prediction.get("outcome") != "success":
                return "single-choice success response has non-success outcome"
            if prediction.get("primary_failure_mode") is not None or failure_modes:
                return "single-choice success response contains failure mode"
        else:
            if prediction.get("outcome") != "failure":
                return "single-choice failure response has non-failure outcome"
            if prediction.get("primary_failure_mode") != choice:
                return "single-choice primary_failure_mode does not match choice"
            if failure_modes != [choice]:
                return "single-choice failure_modes must contain only choice"
        if not isinstance(prediction.get("reasoning"), str):
            return "single-choice response missing reasoning string"
    return None


def extract_reasoning(response: dict[str, Any]) -> str | None:
    choices = response.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    reasoning = message.get("reasoning")
    if reasoning is None:
        return None
    if isinstance(reasoning, str):
        return reasoning
    return json.dumps(reasoning)


def expected_for_task(sample: BenchmarkSample, task_name: str) -> dict[str, Any]:
    if task_name == "binary_success":
        return {"success": sample.expected_outcome == "success"}
    if task_name == "failure_mode_classification":
        return {
            "outcome": sample.expected_outcome,
            "failure_modes": sample.expected_failure_modes,
        }
    if task_name == "single_choice_multiclass":
        choice = "success"
        if sample.expected_outcome != "success":
            modes = sample.expected_failure_modes
            choice = modes[0] if modes else "other_failure"
        return {
            "choice": choice,
            "outcome": sample.expected_outcome,
            "primary_failure_mode": None if choice == "success" else choice,
        }
    raise ValueError(f"Unsupported task: {task_name}")


def build_payload(
    *,
    model: str,
    task_name: str,
    sample: BenchmarkSample,
    videos: list[dict[str, Any]],
    config: dict[str, Any],
    encode_media: bool = True,
) -> dict[str, Any]:
    openrouter_config = config["openrouter"]
    media_config = config.get("media", {})
    payload = {
        "model": model,
        "messages": build_messages(
            load_prompt(task_name),
            videos,
            encode_media=encode_media,
            media_input_type=media_config.get("input_type", "video"),
        ),
        "max_completion_tokens": openrouter_config.get("max_completion_tokens", 700),
        "stream": False,
        "metadata": {
            "benchmark": config["name"],
            "task": task_name,
            "sample_id": sample.sample_id,
        },
    }
    if "temperature" in openrouter_config and openrouter_config["temperature"] is not None:
        payload["temperature"] = openrouter_config["temperature"]
    if "reasoning" in openrouter_config:
        payload["reasoning"] = openrouter_config["reasoning"]
    if openrouter_config.get("require_structured_output", True):
        payload["response_format"] = build_response_format(task_name)
        payload["provider"] = {
            "require_parameters": True,
        }
    return payload


def manifest_record(
    model: str,
    task_name: str,
    sample: BenchmarkSample,
    videos: list[dict[str, Any]],
    media_config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "model": model,
        "task": task_name,
        "sample_id": sample.sample_id,
        "sample_path": sample.metadata["relative_path"],
        "task_id": sample.task_id,
        "expected": expected_for_task(sample, task_name),
        "videos": [
            {
                "file_name": video["file_name"],
                "relative_path": video["relative_path"],
                "camera_view": video["camera_view"],
                "bytes": video["bytes"],
                "sha256": video.get("sha256"),
                "api_media": video.get(
                    "api_media",
                    {
                        "preprocessed": False,
                        "source_path": str(video["path"]),
                        "source_sha256": video.get("sha256"),
                        "api_sha256": video.get("sha256"),
                        "delivery": "base64_data_url",
                        "fairness_profile": media_config.get("fairness_profile"),
                    },
                ),
            }
            for video in videos
        ],
    }


def combo_id(model: str, task_name: str, sample_id: str) -> str:
    return "__".join([safe_name(model), safe_name(task_name), safe_name(sample_id)])


def already_completed(predictions_path: Path) -> set[str]:
    completed: set[str] = set()
    if not predictions_path.exists():
        return completed
    for line in predictions_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("status") == "completed":
            completed.add(record["combo_id"])
    return completed


def update_state(run_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_write_json(run_dir / "state.json", state)


def run_benchmark(args: argparse.Namespace) -> Path:
    config = read_json(Path(args.config))
    models = list(args.model or config.get("models") or [])
    if not models:
        raise RuntimeError("No model configured. Pass --model <openrouter/model-id>.")

    if not args.dry_run:
        for model in models:
            if model.startswith("REPLACE_"):
                raise RuntimeError("Replace placeholder model IDs before making API calls.")
            if model.startswith("~") or model.endswith("-latest") or "latest" in model:
                raise RuntimeError(
                    f"Model aliases are not allowed for reproducible runs: {model}. "
                    "Use an exact OpenRouter model ID."
                )

    tasks = list(args.task or config["tasks"])
    samples = filter_samples(
        load_samples(Path(config["metadata_path"])),
        config.get("sample_filter"),
    )
    if args.limit:
        samples = samples[: args.limit]

    run_id = args.run_id or f"{utc_stamp()}_{safe_name(config['name'])}"
    run_dir = Path(config.get("output_root", "runs")) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(run_dir / "run_config.json", config)

    media_config = config["media"]
    dataset_root = Path(read_json(Path(config["metadata_path"]))["dataset"]["local_root"])
    max_total_bytes = int(media_config["max_total_video_mb_per_request"] * 1024 * 1024)

    predictions_path = run_dir / "predictions.jsonl"
    completed = already_completed(predictions_path)
    client = OpenRouterClient(config["openrouter"])
    state = {
        "run_id": run_id,
        "status": "running",
        "dry_run": args.dry_run,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "completed": len(completed),
        "failed": 0,
        "skipped": 0,
        "planned": len(models) * len(tasks) * len(samples),
    }
    update_state(run_dir, state)

    for model in models:
        for task_name in tasks:
            for sample in samples:
                videos = select_videos(
                    sample,
                    dataset_root,
                    media_config.get("camera_views", []),
                    int(media_config.get("max_videos_per_sample", 0)),
                )
                record_id = combo_id(model, task_name, sample.sample_id)
                videos = maybe_transcode_videos(
                    videos,
                    run_dir / "media_cache" / sample.sample_id,
                    media_config,
                )
                append_jsonl(
                    run_dir / "manifest.jsonl",
                    manifest_record(model, task_name, sample, videos, media_config),
                )

                if record_id in completed and not args.force:
                    state["skipped"] += 1
                    update_state(run_dir, state)
                    continue

                total_bytes = sum(video["bytes"] for video in videos)
                if total_bytes > max_total_bytes:
                    error_record = {
                        "combo_id": record_id,
                        "status": "error",
                        "error": (
                            f"Selected videos total {total_bytes} bytes, exceeding "
                            f"limit {max_total_bytes} bytes."
                        ),
                        "sample_id": sample.sample_id,
                        "model": model,
                        "task": task_name,
                    }
                    append_jsonl(run_dir / "errors.jsonl", error_record)
                    state["failed"] += 1
                    update_state(run_dir, state)
                    continue

                started_at = datetime.now(timezone.utc).isoformat()
                sample_dir = run_dir / "artifacts" / record_id
                sample_dir.mkdir(parents=True, exist_ok=True)

                try:
                    payload = build_payload(
                        model=model,
                        task_name=task_name,
                        sample=sample,
                        videos=videos,
                        config=config,
                        encode_media=not args.dry_run,
                    )
                    atomic_write_json(sample_dir / "request.redacted.json", redact_payload(payload))

                    if args.dry_run:
                        response = {
                            "dry_run": True,
                            "choices": [{"message": {"content": "{}"}}],
                        }
                        content = "{}"
                        reasoning = None
                        prediction = None
                        parse_error = None
                    else:
                        response = client.send(payload)
                        content = extract_content(response)
                        reasoning = extract_reasoning(response)
                        prediction, parse_error = parse_prediction(content)
                        validation_error = validate_prediction(task_name, prediction)
                        if validation_error is not None:
                            parse_error = validation_error
                            prediction = None

                    atomic_write_json(sample_dir / "response.json", response)
                    (sample_dir / "model_output.txt").write_text(content, encoding="utf-8")
                    reasoning_artifact = None
                    if reasoning is not None:
                        reasoning_artifact = sample_dir / "model_reasoning.txt"
                        reasoning_artifact.write_text(reasoning, encoding="utf-8")
                    result = {
                        "combo_id": record_id,
                        "status": "completed" if parse_error is None else "parse_error",
                        "run_id": run_id,
                        "model": model,
                        "task": task_name,
                        "sample_id": sample.sample_id,
                        "sample_path": sample.metadata["relative_path"],
                        "expected": expected_for_task(sample, task_name),
                        "prediction": prediction,
                        "parse_error": parse_error,
                        "raw_output": content,
                        "dry_run": args.dry_run,
                        "started_at_utc": started_at,
                        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                        "response_artifact": str(sample_dir / "response.json"),
                        "raw_output_artifact": str(sample_dir / "model_output.txt"),
                        "raw_reasoning_artifact": (
                            str(reasoning_artifact) if reasoning_artifact is not None else None
                        ),
                    }
                    append_jsonl(predictions_path, result)
                    state["completed"] += 1
                    update_state(run_dir, state)
                except Exception as exc:
                    error_record = {
                        "combo_id": record_id,
                        "status": "error",
                        "error": str(exc),
                        "sample_id": sample.sample_id,
                        "model": model,
                        "task": task_name,
                        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                    append_jsonl(run_dir / "errors.jsonl", error_record)
                    state["failed"] += 1
                    update_state(run_dir, state)

    state["status"] = "completed"
    update_state(run_dir, state)
    return run_dir


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run LabOS-Sim OpenRouter benchmarks.")
    parser.add_argument(
        "--config",
        default="configs/benchmarks/vortexing_openrouter.json",
        help="Benchmark config JSON path.",
    )
    parser.add_argument("--model", action="append", help="OpenRouter model ID. Repeatable.")
    parser.add_argument(
        "--task",
        action="append",
        choices=["binary_success", "failure_mode_classification", "single_choice_multiclass"],
        help="Benchmark task. Repeatable; defaults to config tasks.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples.")
    parser.add_argument("--run-id", default=None, help="Explicit run directory name.")
    parser.add_argument("--dry-run", action="store_true", help="Build artifacts without API calls.")
    parser.add_argument("--force", action="store_true", help="Rerun completed sample/model/task combos.")
    return parser
