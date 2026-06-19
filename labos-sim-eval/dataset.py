from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class LabOSSample:
    sample_id: str
    relative_path: str
    expected_choice: str
    outcome: str
    videos: list[dict[str, Any]]
    metadata: dict[str, Any]


def expected_choice(sample: dict[str, Any]) -> str:
    if sample.get("is_success"):
        return "success"
    modes = sample.get("failure_modes") or []
    return modes[0] if modes else "other_failure"


def load_samples(metadata_path: str | Path) -> list[LabOSSample]:
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    samples = []
    for sample in metadata["samples"]:
        samples.append(
            LabOSSample(
                sample_id=sample["sample_id"],
                relative_path=sample["relative_path"],
                expected_choice=expected_choice(sample),
                outcome=sample["outcome"],
                videos=list(sample.get("videos") or []),
                metadata=sample,
            )
        )
    return samples


def filter_samples(
    samples: Iterable[LabOSSample],
    *,
    split_ids: set[str] | None = None,
    exclude_condition_folders: set[str] | None = None,
    max_samples: int | None = None,
) -> list[LabOSSample]:
    out: list[LabOSSample] = []
    for sample in samples:
        if split_ids is not None and sample.sample_id not in split_ids:
            continue
        if exclude_condition_folders and sample.metadata.get("condition_folder") in exclude_condition_folders:
            continue
        out.append(sample)
        if max_samples and len(out) >= max_samples:
            break
    return out


def resolve_sample_media(
    sample: LabOSSample,
    *,
    data_root: str | Path,
    camera_views: list[str] | None = None,
    max_videos: int = 0,
    input_mode: str = "video",
) -> list[dict[str, Any]]:
    """Return the standardized media records every adapter starts from."""
    root = Path(data_root)
    views = set(camera_views or [])
    records: list[dict[str, Any]] = []
    for video in sample.videos:
        if views and video.get("camera_view") not in views:
            continue
        path = root / sample.relative_path / video["file_name"]
        records.append(
            {
                "type": "video" if input_mode == "video" else input_mode,
                "path": str(path.resolve()),
                "file_name": video["file_name"],
                "camera_view": video.get("camera_view"),
                "camera_device": video.get("camera_device"),
                "bytes": video.get("bytes"),
                "sample_id": sample.sample_id,
            }
        )
        if max_videos and len(records) >= max_videos:
            break
    return records
