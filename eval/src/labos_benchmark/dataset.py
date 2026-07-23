"""Dataset layer: the DataPoint dataclass + loaders for metadata / run lists.

A **DataPoint** is one clip (one evaluation sample): a unified index, its
operation/task category, its ground-truth label, and its set of camera-angle
videos. Video paths are stored relative to the top-level `data/` directory so a
single `data_root` resolves any dataset subfolder (real_human, robotic_arm, ...).

Catalogs are JSONL:
  * data/{dataset}/metadata.jsonl  — the full per-dataset catalog (one DataPoint/line)
  * data/*run_list*.jsonl          — a selection to actually run (subset or full)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[3] / "data"


@dataclass(frozen=True)
class DataPoint:
    """One clip / evaluation sample."""

    index: int                       # unified index across the catalog
    sample_id: str                   # stable human-readable id
    operation: str                   # task category, e.g. "vortexing"
    dataset: str                     # data subfolder, e.g. "real_human"
    relative_path: str               # clip folder, relative to data/
    outcome: str                     # ground-truth: "success" | "failure"
    failure_modes: list[str]         # ground-truth failure subtypes ([] if success)
    video_count: int
    videos: list[dict[str, Any]] = field(default_factory=list)  # {camera_view, file}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DataPoint":
        return cls(
            index=int(d["index"]),
            sample_id=d["sample_id"],
            operation=d.get("operation", "unknown"),
            dataset=d.get("dataset", ""),
            relative_path=d.get("relative_path", ""),
            outcome=d.get("outcome", "failure" if d.get("failure_modes") else "success"),
            failure_modes=list(d.get("failure_modes") or []),
            video_count=int(d.get("video_count", len(d.get("videos") or []))),
            videos=list(d.get("videos") or []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index, "sample_id": self.sample_id, "operation": self.operation,
            "dataset": self.dataset, "relative_path": self.relative_path,
            "outcome": self.outcome, "failure_modes": self.failure_modes,
            "video_count": self.video_count, "videos": self.videos,
        }

    @property
    def expected(self) -> dict[str, Any]:
        """Ground-truth label, written into each prediction record."""
        return {"outcome": self.outcome, "failure_modes": self.failure_modes}

    def resolve_videos(self, data_root: str | Path = DEFAULT_DATA_ROOT,
                       camera_views: list[str] | None = None) -> list[dict[str, Any]]:
        """Return [{camera_view, file, path}], ordered by camera_views if given.

        `path` is the on-disk path (data_root / file).
        """
        root = Path(data_root)
        if camera_views:
            by_view = {str(v.get("camera_view")): v for v in self.videos}
            selected = [by_view[view] for view in camera_views if view in by_view]
        else:
            selected = self.videos
        return [{**v, "path": str(root / v["file"])} for v in selected]


def load_datapoints(jsonl_path: str | Path) -> list[DataPoint]:
    """Load a metadata.jsonl or run_list.jsonl into DataPoint objects."""
    path = Path(jsonl_path)
    points = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            points.append(DataPoint.from_dict(json.loads(line)))
    return points


def write_datapoints(jsonl_path: str | Path, points: list[DataPoint]) -> None:
    path = Path(jsonl_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for p in points:
            f.write(json.dumps(p.to_dict()) + "\n")
