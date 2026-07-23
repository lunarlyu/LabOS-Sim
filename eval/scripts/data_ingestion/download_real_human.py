from __future__ import annotations

import argparse
import csv
from pathlib import Path

from huggingface_hub import snapshot_download


DEFAULT_REPO_ID = "labos-sim/real_human"
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data/real_human"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the LabOS-Sim real_human dataset from Hugging Face."
    )
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--token",
        default=None,
        help="Optional Hugging Face token. You can also set HF_TOKEN in your environment.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional selected_samples CSV; download only those sample folders.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    allow_patterns = None
    if args.manifest is not None:
        with args.manifest.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        sample_dirs = set()
        for row in rows:
            relative = Path(row["relative_path"])
            if relative.parts and relative.parts[0] == "real_human":
                relative = Path(*relative.parts[1:])
            sample_dirs.add(relative.as_posix())
        allow_patterns = ["metadata.jsonl"] + [f"{path}/*.mp4" for path in sorted(sample_dirs)]
        print(f"Selecting {len(sample_dirs)} sample folders from {args.manifest}")

    path = snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        local_dir=output_dir,
        token=args.token,
        allow_patterns=allow_patterns,
    )
    print(f"Downloaded {args.repo_id} to {path}")


if __name__ == "__main__":
    main()
