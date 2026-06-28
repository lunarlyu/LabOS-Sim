"""Output schemas, keyed by prompt_type.

These describe the JSON each prompt is expected to return. P1/P3 are structured
(usable as an OpenAI-style ``response_format`` where the provider supports it);
P2 is freeform (its output is later mapped by P6); P6 is the parser's schema.
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

# --- p3: multi-label classification -----------------------------------------
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
    "required": ["outcome", "failure_modes", "confidence", "reasoning"],
    "additionalProperties": False,
}

# --- p2: open detection (freeform; parsed later by p6) ----------------------
OPEN_DETECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "error_present": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "observed_errors": {"type": "array", "items": {"type": "string"},
                            "description": "Empty / 'None' iff error_present is false."},
        "reasoning": {"type": "string"},
    },
    "required": ["error_present", "confidence", "observed_errors", "reasoning"],
    "additionalProperties": False,
}

# --- p6: freetext → subtype parser ------------------------------------------
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
    "required": ["outcome", "failure_modes", "confidence", "reasoning"],
    "additionalProperties": False,
}

SCHEMA_BY_PROMPT = {
    "closed_binary": CLOSED_BINARY_SCHEMA,
    "multilabel_classification": MULTILABEL_SCHEMA,
    "open_detection": OPEN_DETECTION_SCHEMA,
    "freetext_parser": PARSER_SCHEMA,
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
