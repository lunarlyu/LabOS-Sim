from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from labos_benchmark.runner import build_arg_parser, run_benchmark


def main() -> None:
    args = build_arg_parser().parse_args()
    run_dir = run_benchmark(args)
    print(f"Benchmark artifacts written to {run_dir}")


if __name__ == "__main__":
    main()
