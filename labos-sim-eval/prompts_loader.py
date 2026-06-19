from __future__ import annotations

from pathlib import Path


def load_prompt(prompt_root: str | Path, prompt_id: str) -> str:
    path = Path(prompt_root) / f"{prompt_id}.txt"
    return path.read_text(encoding="utf-8")


def load_prompt_with_protocol(prompt_root: str | Path, prompt_id: str, protocol_file: str) -> str:
    root = Path(prompt_root)
    template = (root / f"{prompt_id}.txt").read_text(encoding="utf-8")
    protocol = (root / protocol_file).read_text(encoding="utf-8")
    return template.replace("{protocol}", protocol)
