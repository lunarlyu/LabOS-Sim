from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import read_json


@dataclass(frozen=True)
class BenchmarkSample:
    sample_id: str
    metadata: dict[str, Any]

    @property
    def task_id(self) -> str:
        return self.metadata["task"]["task_id"]

    @property
    def expected_outcome(self) -> str:
        return self.metadata["outcome"]

    @property
    def expected_failure_modes(self) -> list[str]:
        return list(self.metadata.get("failure_modes", []))


def load_samples(metadata_path: Path) -> list[BenchmarkSample]:
    metadata = read_json(metadata_path)
    return [
        BenchmarkSample(sample_id=sample["sample_id"], metadata=sample)
        for sample in metadata["samples"]
    ]


def filter_samples(
    samples: list[BenchmarkSample],
    sample_filter: dict[str, Any] | None,
) -> list[BenchmarkSample]:
    if not sample_filter:
        return samples

    task_ids = set(sample_filter.get("task_ids") or [])
    include_sample_ids = set(sample_filter.get("include_sample_ids") or [])
    exclude_sample_ids = set(sample_filter.get("exclude_sample_ids") or [])

    filtered: list[BenchmarkSample] = []
    for sample in samples:
        if include_sample_ids and sample.sample_id not in include_sample_ids:
            continue
        if task_ids and sample.task_id not in task_ids:
            continue
        if sample.sample_id in exclude_sample_ids:
            continue
        filtered.append(sample)
    return filtered


def select_videos(
    sample: BenchmarkSample,
    dataset_root: Path,
    camera_views: list[str],
    max_videos: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    wanted = set(camera_views)
    for video in sample.metadata["videos"]:
        if wanted and video["camera_view"] not in wanted:
            continue
        video_path = dataset_root / "video_Carrie" / video["relative_path"]
        selected.append({**video, "path": video_path})
        if max_videos and len(selected) >= max_videos:
            break
    return selected

