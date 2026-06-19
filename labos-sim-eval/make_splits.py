from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from dataset import load_samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Create LabOS-Sim eval split files.")
    parser.add_argument("--metadata", default="../metadata/real_human_samples_no_multiple.json")
    parser.add_argument("--output", default="splits/smoke.json")
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    samples = load_samples(args.metadata)
    rng = random.Random(args.seed)
    chosen = list(samples)
    rng.shuffle(chosen)
    chosen = chosen[: args.n]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"sample_ids": [sample.sample_id for sample in chosen]}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
