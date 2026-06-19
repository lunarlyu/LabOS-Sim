from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATASET_REPO_ID = "labos-sim/real_human"
DEFAULT_DATASET_ROOT = Path("data") / "real_human"
DEFAULT_VIDEO_ROOT = DEFAULT_DATASET_ROOT / "video_Carrie"
DEFAULT_OUTPUT = Path("metadata") / "real_human_samples.json"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
EXPECTED_CAMERA_FILES = {
    "camera-front_lower_zed_x_mini.mp4",
    "camera-front_zed_x_mini.mp4",
    "camera-gripper_zed_x_mini.mp4",
    "camera-left_zed_x.mp4",
    "camera-right_zed_x.mp4",
}


FAILURE_MODE_DESCRIPTIONS = {
    "cap_open": "Tube cap is open, loose, or otherwise not properly closed.",
    "tube_drop": "Tube is dropped during the scenario.",
    "tube_empty": "Tube is empty when it should contain liquid or sample material.",
    "vortex_off": "Vortex mixer is off when it should be active.",
    "wrong_orientation": "Tube, rack, or relevant object orientation is incorrect.",
    "wrong_rack": "Tube is placed in or associated with the wrong rack.",
    "rack_flipped": "Rack is flipped or inverted relative to the expected setup.",
    "repeated_steps": "Actor appears to repeat one or more procedural steps.",
}

TASK_DEFINITIONS = {
    "basic_vortexing": {
        "name": "Basic vortexing",
        "description": (
            "Complete the standard vortexing workflow with a correctly selected rack, "
            "a non-empty tube, and no observed procedural failure."
        ),
        "success_states": ["clean", "correct_rack", "tube_nonempty"],
    },
    "closing_cap": {
        "name": "Closing the cap task",
        "description": "Ensure the tube cap is properly closed.",
        "success_states": ["cap_close"],
    },
    "vortexing_after_turning_on_vortexer": {
        "name": "Vortexing after turning on the vortexer",
        "description": "Turn on the vortexer and then complete the vortexing workflow.",
        "success_states": ["vortex_on"],
    },
    "ambiguous_multiple_task": {
        "name": "Ambiguous or multiple-task failure",
        "description": (
            "The path indicates an unusual or combined failure case that does not map "
            "cleanly to one task without review."
        ),
        "success_states": [],
    },
}

SUCCESS_STATE_TO_TASK_ID = {
    state: task_id
    for task_id, definition in TASK_DEFINITIONS.items()
    for state in definition["success_states"]
}

FAILURE_MODE_TO_TASK_ID = {
    "cap_open": "closing_cap",
    "tube_drop": "basic_vortexing",
    "tube_empty": "basic_vortexing",
    "vortex_off": "vortexing_after_turning_on_vortexer",
    "wrong_orientation": "basic_vortexing",
    "wrong_rack": "basic_vortexing",
    "rack_flipped": "basic_vortexing",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate path-derived metadata for the LabOS-Sim real_human videos."
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--video-root", type=Path, default=DEFAULT_VIDEO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def slug_words(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def parse_condition(condition_folder: str) -> tuple[int | None, str]:
    match = re.match(r"^(?P<index>\d+)_(?P<name>.+)$", condition_folder)
    if match:
        return int(match.group("index")), match.group("name")
    return None, condition_folder


def parse_trial_number(sample_name: str) -> int | None:
    match = re.search(r"(?:^|_)(\d+)(?:_|$)", sample_name)
    if match:
        return int(match.group(1))
    return None


def scenario_tags(sample_name: str) -> list[str]:
    base = re.sub(r"^(success|fail)_", "", sample_name)
    base = re.sub(r"(^|_)\d+(_|$)", r"\1", base).strip("_")
    return [base] if base else []


def scenario_failure_modes(condition_name: str, sample_name: str) -> list[str]:
    if condition_name == "success":
        return []

    tags = scenario_tags(sample_name)
    if condition_name != "multiple":
        return [condition_name]

    modes: list[str] = []
    for tag in tags:
        if tag == "vortex_off_tube_empty":
            modes.extend(["vortex_off", "tube_empty"])
        else:
            modes.append(tag)
    return modes


def task_metadata(
    is_success: bool, scenario_tags_: list[str], failure_modes: list[str]
) -> dict[str, Any]:
    success_state = None
    candidate_task_ids: list[str] = []
    inference_source = "path"
    confidence = "initial_best_effort"

    if is_success:
        success_state = scenario_tags_[0] if scenario_tags_ else None
        task_id = SUCCESS_STATE_TO_TASK_ID.get(success_state, "ambiguous_multiple_task")
        candidate_task_ids = [task_id]
        confidence = "high_path_derived" if task_id != "ambiguous_multiple_task" else confidence
    else:
        candidate_task_ids = sorted(
            {
                task_id
                for mode in failure_modes
                if (task_id := FAILURE_MODE_TO_TASK_ID.get(mode)) is not None
            }
        )
        if len(candidate_task_ids) == 1:
            task_id = candidate_task_ids[0]
        else:
            task_id = "ambiguous_multiple_task"

    definition = TASK_DEFINITIONS[task_id]
    return {
        "task_id": task_id,
        "task_name": definition["name"],
        "task_description": definition["description"],
        "success_state": success_state,
        "task_success_states": definition["success_states"],
        "candidate_task_ids": candidate_task_ids,
        "task_inference": {
            "source": inference_source,
            "confidence": confidence,
            "notes": (
                "Success tasks are inferred from normalized success-state tags. "
                "Failure tasks are inferred from the failure mode when possible."
            ),
        },
    }


def camera_metadata(video_path: Path, video_root: Path) -> dict[str, Any]:
    stem = video_path.stem
    camera_name = stem.removeprefix("camera-")
    device = None
    camera_view = camera_name

    for known_device in ("zed_x_mini", "zed_x"):
        suffix = f"_{known_device}"
        if camera_name.endswith(suffix):
            camera_view = camera_name[: -len(suffix)]
            device = known_device
            break

    return {
        "file_name": video_path.name,
        "relative_path": video_path.relative_to(video_root).as_posix(),
        "camera_view": camera_view,
        "camera_device": device,
        "bytes": video_path.stat().st_size,
    }


def build_sample(sample_dir: Path, dataset_root: Path, video_root: Path) -> dict[str, Any]:
    condition_folder = sample_dir.parent.name
    condition_index, condition_name = parse_condition(condition_folder)
    sample_name = sample_dir.name
    is_success = condition_name == "success"
    tags = scenario_tags(sample_name)
    failure_modes = scenario_failure_modes(condition_name, sample_name)
    task = task_metadata(is_success, tags, failure_modes)
    videos = sorted(
        (
            camera_metadata(path, video_root)
            for path in sample_dir.iterdir()
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        ),
        key=lambda item: item["file_name"],
    )
    camera_files = {video["file_name"] for video in videos}

    return {
        "sample_id": slug_words(f"real_human Carrie {condition_folder} {sample_name}"),
        "dataset_repo_id": DATASET_REPO_ID,
        "subject": "Carrie",
        "relative_path": sample_dir.relative_to(dataset_root).as_posix(),
        "condition_folder": condition_folder,
        "condition_index": condition_index,
        "condition_description": condition_name,
        "scenario_name": sample_name,
        "scenario_trial": parse_trial_number(sample_name),
        "scenario_tags": tags,
        "task": task,
        "outcome": "success" if is_success else "failure",
        "is_success": is_success,
        "failure_modes": failure_modes,
        "failure_mode_descriptions": {
            mode: FAILURE_MODE_DESCRIPTIONS.get(mode) for mode in failure_modes
        },
        "label_inference": {
            "source": "path",
            "confidence": "initial_best_effort",
            "notes": (
                "Success/failure labels are inferred from the condition folder. "
                "Scenario tags are inferred from the leaf folder name."
            ),
        },
        "videos": videos,
        "video_count": len(videos),
        "expected_camera_files": sorted(EXPECTED_CAMERA_FILES),
        "missing_camera_files": sorted(EXPECTED_CAMERA_FILES - camera_files),
    }


def generate_metadata(dataset_root: Path, video_root: Path) -> dict[str, Any]:
    sample_dirs = sorted(
        path for path in video_root.glob("*/*") if path.is_dir() and not path.name.startswith(".")
    )
    samples = [build_sample(path, dataset_root, video_root) for path in sample_dirs]
    failure_counts: dict[str, int] = {}
    for sample in samples:
        for mode in sample["failure_modes"]:
            failure_counts[mode] = failure_counts.get(mode, 0) + 1
    task_counts: dict[str, int] = {}
    success_state_counts: dict[str, int] = {}
    for sample in samples:
        task_id = sample["task"]["task_id"]
        task_counts[task_id] = task_counts.get(task_id, 0) + 1
        success_state = sample["task"]["success_state"]
        if success_state is not None:
            success_state_counts[success_state] = success_state_counts.get(success_state, 0) + 1

    return {
        "schema_version": "0.2.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/generate_real_human_metadata.py",
        "dataset": {
            "repo_id": DATASET_REPO_ID,
            "local_root": dataset_root.as_posix(),
            "video_root": video_root.as_posix(),
            "subject": "Carrie",
        },
        "assumptions": [
            "Each leaf scenario folder under video_Carrie is one evaluation sample.",
            "The parent condition folder supplies the primary success or failure label.",
            "Success leaf-folder tags define the task success state.",
            "The multiple folder uses the leaf folder name to infer specific failure modes.",
            "Camera files within a sample are alternate views of the same scenario.",
            "Labels are path-derived and should be treated as initial metadata until reviewed.",
        ],
        "summary": {
            "sample_count": len(samples),
            "success_count": sum(1 for sample in samples if sample["is_success"]),
            "failure_count": sum(1 for sample in samples if not sample["is_success"]),
            "task_counts": dict(sorted(task_counts.items())),
            "success_state_counts": dict(sorted(success_state_counts.items())),
            "failure_mode_counts": dict(sorted(failure_counts.items())),
            "samples_with_missing_cameras": [
                sample["sample_id"] for sample in samples if sample["missing_camera_files"]
            ],
        },
        "task_definitions": TASK_DEFINITIONS,
        "failure_mode_descriptions": FAILURE_MODE_DESCRIPTIONS,
        "samples": samples,
    }


def main() -> None:
    args = parse_args()
    metadata = generate_metadata(args.dataset_root, args.video_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(metadata['samples'])} samples to {args.output}")


if __name__ == "__main__":
    main()
