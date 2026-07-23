from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_name(value: str) -> str:
    clean = []
    for char in value.lower():
        if char.isalnum():
            clean.append(char)
        elif char in {"-", "_", ".", "/"}:
            clean.append("_")
        else:
            clean.append("_")
    return "_".join(part for part in "".join(clean).split("_") if part)


def setup_keys(env_json_path: str | Path = REPO_ROOT / "_env.json") -> None:
    """Load API keys from a local _env.json into os.environ (adapted from brdm).

    Silently no-ops if the file is absent so CI / collaborators without the file
    can still import the package.
    """
    path = Path(env_json_path)
    if not path.is_file():
        return
    env_vars = json.loads(path.read_text(encoding="utf-8"))
    for key, value in env_vars.items():
        os.environ.setdefault(key, str(value))
