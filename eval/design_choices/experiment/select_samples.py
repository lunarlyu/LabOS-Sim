#!/usr/bin/env python3
"""Create a reproducible class-balanced manifest for the design-choice experiment."""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = EVAL_ROOT.parent
CLASS_ORDER = [
    "success", "cap_open", "tube_drop", "tube_empty", "vortex_off",
    "wrong_orientation", "wrong_rack", "rack_flipped",
]


def primary_type(row: dict) -> str:
    modes = list(row.get("failure_modes") or [])
    if row.get("outcome") == "success" or not modes:
        return "success"
    if len(modes) != 1:
        raise ValueError(f"expected one failure type for {row.get('sample_id')}: {modes}")
    return str(modes[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-per-type", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260711)
    parser.add_argument(
        "--output", type=Path,
        default=EVAL_ROOT / "design_choices/experiment/selected_samples_10_per_type.csv",
    )
    args = parser.parse_args()

    catalog_path = REPO_ROOT / "data/real_human/metadata.jsonl"
    catalog = [
        json.loads(line)
        for line in catalog_path.read_text().splitlines()
        if line.strip()
    ]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in catalog:
        grouped[primary_type(row)].append(row)

    rng = random.Random(args.seed)
    selected: list[tuple[str, int, dict]] = []
    for label in CLASS_ORDER:
        candidates = sorted(grouped[label], key=lambda row: row["sample_id"])
        if len(candidates) < args.samples_per_type:
            raise SystemExit(
                f"{label} has {len(candidates)} samples; cannot select {args.samples_per_type}"
            )
        for rank, row in enumerate(rng.sample(candidates, args.samples_per_type), start=1):
            selected.append((label, rank, row))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "selection_group",
                "selection_rank",
                "sample_id",
                "relative_path",
                "sampling_seed",
            ],
        )
        writer.writeheader()
        for label, rank, row in selected:
            writer.writerow({
                "selection_group": label,
                "selection_rank": rank,
                "sample_id": row["sample_id"],
                "relative_path": row["relative_path"],
                "sampling_seed": args.seed,
            })
    print(f"wrote {len(selected)} samples ({args.samples_per_type}/type) to {args.output}")


if __name__ == "__main__":
    main()
