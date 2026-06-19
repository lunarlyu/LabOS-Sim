from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


DEFAULT_REPO_ID = "labos-sim/real_human"
DEFAULT_OUTPUT_DIR = Path("data") / "real_human"


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    path = snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        local_dir=output_dir,
        token=args.token,
    )
    print(f"Downloaded {args.repo_id} to {path}")


if __name__ == "__main__":
    main()

