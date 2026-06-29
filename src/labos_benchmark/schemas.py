"""Output schemas, keyed by prompt_type.

These describe the JSON each prompt is expected to return. P1/P2 emit the
standard scoring schema directly; P3/P4 emit structured free-text fields that
are mapped by P5/P6 parser prompts.
Taxonomy matches prompts/PROMPT_CATALOG.md — ``repeated_steps`` removed.
"""
from __future__ import annotations

from .prompts import prompt_type_of

FAILURE_LABELS = [
    "cap_open",
    "tube_drop",
    "tube_empty",
    "vortex_off",
    "wrong_orientation",
    "wrong_rack",
    "rack_flipped",
    "other_failure",
]

_ADDITIONAL_FAILURES = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "evidence": {"type": "string"},
        },
        "required": ["description", "evidence"],
        "additionalProperties": False,
    },
    "description": "Non-empty iff 'other_failure' is in failure_modes.",
}

# --- p1: closed binary -------------------------------------------------------
CLOSED_BINARY_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["success", "failure"]},
        "failure_modes": {"type": "array", "items": {"type": "string"},
                          "description": "Always empty for this prompt."},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string"},
    },
    "required": ["outcome", "failure_modes", "confidence", "reasoning"],
    "additionalProperties": False,
}

# --- p2: multi-label classification -----------------------------------------
MULTILABEL_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["success", "failure"]},
        "failure_modes": {"type": "array", "items": {"type": "string", "enum": FAILURE_LABELS},
                          "description": "Empty iff success; ordered most-important first."},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string"},
        "additional_failures": _ADDITIONAL_FAILURES,
    },
    "required": ["outcome", "failure_modes", "confidence", "reasoning", "additional_failures"],
    "additionalProperties": False,
}

# --- p3: open detection, STRICT (error-aware; parsed later by p5) ------------
OPEN_DETECTION_STRICT_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["success", "failure"]},
        "observed_errors": {"type": "string",
                            "description": "Comma-separated errors; 'None' iff outcome is success."},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["outcome", "observed_errors", "confidence"],
    "additionalProperties": False,
}

# --- p4: open detection, FREE (description; error-unaware; parsed by p6) -----
OPEN_DETECTION_FREE_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["success", "failure"]},
        "description": {"type": "string",
                        "description": "Free-text account of the video; always present."},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["outcome", "description", "confidence"],
    "additionalProperties": False,
}

# --- p5 / p6: parser output (shared standardized schema) ---------------------
PARSER_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["success", "failure", "ambiguous"]},
        "failure_modes": {"type": "array", "items": {"type": "string", "enum": FAILURE_LABELS}},
        "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1,
                       "description": "null when the source model gave none."},
        "reasoning": {"type": "string"},
        "additional_failures": _ADDITIONAL_FAILURES,
        "ambiguous_mentions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "candidate_modes": {"type": "array", "items": {"type": "string"}},
                    "why": {"type": "string"},
                },
                "required": ["text", "candidate_modes", "why"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "outcome",
        "failure_modes",
        "confidence",
        "reasoning",
        "additional_failures",
        "ambiguous_mentions",
    ],
    "additionalProperties": False,
}

SCHEMA_BY_PROMPT = {
    "closed_binary": CLOSED_BINARY_SCHEMA,
    "multilabel_classification": MULTILABEL_SCHEMA,
    "open_detection_strict": OPEN_DETECTION_STRICT_SCHEMA,
    "open_detection_free": OPEN_DETECTION_FREE_SCHEMA,
    "open_detection_strict_parser": PARSER_SCHEMA,
    "open_detection_free_parser": PARSER_SCHEMA,
}


def schema_for_task(task_name: str) -> dict:
    """Return the JSON schema for a task name (e.g. 'vortex_multilabel_classification')."""
    return SCHEMA_BY_PROMPT[prompt_type_of(task_name)]


def response_format_for_task(task_name: str) -> dict:
    """Wrap the schema as an OpenAI-style json_schema response_format."""
    ptype = prompt_type_of(task_name)
    return {
        "type": "json_schema",
        "json_schema": {"name": ptype, "strict": True, "schema": SCHEMA_BY_PROMPT[ptype]},
    }
