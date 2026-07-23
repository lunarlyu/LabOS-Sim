"""Prompt loading and the task → prompt registry.

Task naming convention: ``task_name = "{operation}_{prompt_type}"`` so that when
we add operations beyond vortexing the same machinery applies
(e.g. ``vortex_multilabel_classification`` → later ``pipette_multilabel_classification``).
The prompt is selected by the *prompt_type* suffix.
"""
from __future__ import annotations

import re
from pathlib import Path

# Evaluation-root-relative prompts directory.
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

# prompt_type → prompt filename. (Prompts are currently vortexing-specific and
# operation-agnostic in location; when multiple operations arrive, move to
# prompts/{operation}/<file> and have get_prompt_path join the operation.)
PROMPT_TYPES: dict[str, str] = {
    "closed_binary": "p1_closed_binary.md",
    "multilabel_classification": "p2_multilabel_classification.md",
    "open_detection_strict": "p3_open_detection_strict.md",
    "open_detection_free": "p4_open_detection_free.md",
    "open_detection_strict_parser": "p5_open_detection_strict_parser.md",
    "open_detection_free_parser": "p6_open_detection_free_parser.md",
}


def is_parser(prompt_type: str) -> bool:
    """Parser prompt types map a prior VLM run's text onto the taxonomy."""
    return prompt_type.endswith("_parser")


def split_task(task_name: str) -> tuple[str, str]:
    """Split ``{operation}_{prompt_type}`` → (operation, prompt_type).

    Matches the longest known prompt_type suffix (prompt types contain
    underscores, so we cannot naively split on the last underscore).
    """
    for ptype in sorted(PROMPT_TYPES, key=len, reverse=True):
        if task_name == ptype or task_name.endswith("_" + ptype):
            operation = task_name[: len(task_name) - len(ptype)].rstrip("_")
            return operation, ptype
    raise ValueError(
        f"Unknown task '{task_name}'. Expected '<operation>_<prompt_type>' with "
        f"prompt_type in {sorted(PROMPT_TYPES)}."
    )


def prompt_type_of(task_name: str) -> str:
    return split_task(task_name)[1]


def get_prompt_path(task_name: str, prompts_dir: Path = PROMPTS_DIR) -> Path:
    """Resolve a task name to its prompt .md file path."""
    _operation, ptype = split_task(task_name)
    return Path(prompts_dir) / PROMPT_TYPES[ptype]


def load_prompt_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def fill_in_prompt(template: str, arguments: dict[str, str]) -> str:
    """Substitute ``{{key}}`` placeholders; warn on any left unfilled.

    Adapted from brdm's prompt.fill_in_prompt — matches the p6 prompt's
    ``{{outcome}}`` / ``{{observed_errors}}`` / ``{{description}}`` scheme.
    """
    for key, value in arguments.items():
        template = template.replace("{{" + key + "}}", str(value))
    unreplaced = re.findall(r"{{(.*?)}}", template)
    if unreplaced:
        print(f"[WARNING] Unreplaced placeholders in prompt: {unreplaced}", flush=True)
    return template


def load_prompt(task_name: str, arguments: dict[str, str] | None = None,
                prompts_dir: Path = PROMPTS_DIR) -> str:
    """Load a task's prompt and optionally fill ``{{}}`` placeholders."""
    text = load_prompt_file(get_prompt_path(task_name, prompts_dir))
    return fill_in_prompt(text, arguments) if arguments else text
