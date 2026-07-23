#!/usr/bin/env python3
"""Build a per-dataset metadata.jsonl catalog (one DataPoint per line).

Converts the source metadata json (data/real_human/source_metadata.json)
into data/{dataset}/metadata.jsonl with video paths relative to data/, so a
single data_root resolves every dataset subfolder.

Schema per line:
  {index, sample_id, operation, dataset, relative_path, outcome,
   failure_modes, video_count, videos:[{camera_view, file}]}

For a new dataset (e.g. robotic_arm) you can either point --input at its legacy
json or extend this script with a folder scanner.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path,
                    default=REPO_ROOT / "data/real_human/source_metadata.json",
                    help="source metadata json to convert")
    ap.add_argument("--dataset", default="real_human", help="data subfolder name")
    ap.add_argument("--video-subdir", default="video_Carrie",
                    help="subdir under data/{dataset} holding the clips")
    ap.add_argument("--operation", default="vortexing", help="task category for these clips")
    ap.add_argument("--out", type=Path, default=None,
                    help="output path (default: data/{dataset}/metadata.jsonl)")
    args = ap.parse_args(argv)

    meta = json.loads(args.input.read_text(encoding="utf-8"))
    samples = meta["samples"] if isinstance(meta, dict) and "samples" in meta else meta
    out_path = args.out or REPO_ROOT / "data" / args.dataset / "metadata.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for i, s in enumerate(samples):
            videos = [
                {"camera_view": v.get("camera_view"),
                 "file": f"{args.dataset}/{args.video_subdir}/{v['relative_path']}"}
                for v in s.get("videos", [])
            ]
            row = {
                "index": i,
                "sample_id": s["sample_id"],
                "operation": args.operation,
                "dataset": args.dataset,
                "relative_path": f"{args.dataset}/{s['relative_path']}",
                "outcome": s.get("outcome", "failure" if s.get("failure_modes") else "success"),
                "failure_modes": list(s.get("failure_modes") or []),
                "video_count": len(videos),
                "videos": videos,
            }
            f.write(json.dumps(row) + "\n")
            n += 1

    print(f"[metadata] wrote {n} datapoints -> {out_path}")


if __name__ == "__main__":
    main()
