from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def collect_run_metadata(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "config_run_name": (config.get("run") or {}).get("name"),
    }


def write_run_metadata(path: str | Path, config: dict[str, Any]) -> None:
    Path(path).write_text(
        json.dumps(collect_run_metadata(config), indent=2) + "\n",
        encoding="utf-8",
    )
