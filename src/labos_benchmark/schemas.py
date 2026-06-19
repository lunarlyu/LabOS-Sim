from __future__ import annotations


FAILURE_MODE_LABELS = [
    "cap_open",
    "tube_drop",
    "tube_empty",
    "vortex_off",
    "wrong_orientation",
    "wrong_rack",
    "rack_flipped",
    "repeated_steps",
    "other_failure",
]

SINGLE_CHOICE_LABELS = ["success"] + FAILURE_MODE_LABELS


BINARY_SUCCESS_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {
            "type": "boolean",
            "description": "True if the vortexing workflow appears successful.",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in the binary decision.",
        },
        "observed_failure": {
            "type": "string",
            "description": "Brief visible failure if unsuccessful, otherwise an empty string.",
        },
        "rationale": {
            "type": "string",
            "description": "Short evidence-based explanation.",
        },
    },
    "required": ["success", "confidence", "observed_failure", "rationale"],
    "additionalProperties": False,
}


FAILURE_MODE_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {
            "type": "string",
            "enum": ["success", "failure"],
            "description": "Overall outcome of the workflow.",
        },
        "failure_modes": {
            "type": "array",
            "items": {"type": "string", "enum": FAILURE_MODE_LABELS},
            "description": "Empty for success; one or more labels for failure.",
        },
        "primary_failure_mode": {
            "type": ["string", "null"],
            "enum": FAILURE_MODE_LABELS + [None],
            "description": "Most salient failure mode, or null for success.",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in the classification.",
        },
        "rationale": {
            "type": "string",
            "description": "Short evidence-based explanation.",
        },
    },
    "required": [
        "outcome",
        "failure_modes",
        "primary_failure_mode",
        "confidence",
        "rationale",
    ],
    "additionalProperties": False,
}


SINGLE_CHOICE_MULTICLASS_SCHEMA = {
    "type": "object",
    "properties": {
        "choice": {
            "type": "string",
            "enum": SINGLE_CHOICE_LABELS,
            "description": "Exactly one selected outcome label.",
        },
        "outcome": {
            "type": "string",
            "enum": ["success", "failure"],
            "description": "Overall outcome implied by choice.",
        },
        "primary_failure_mode": {
            "type": ["string", "null"],
            "enum": FAILURE_MODE_LABELS + [None],
            "description": "The selected failure mode, or null when choice is success.",
        },
        "failure_modes": {
            "type": "array",
            "items": {"type": "string", "enum": FAILURE_MODE_LABELS},
            "description": "Empty for success; one item matching primary_failure_mode for failure.",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in the selected choice.",
        },
        "reasoning": {
            "type": "string",
            "description": "Short evidence-based explanation for the selected choice.",
        },
    },
    "required": [
        "choice",
        "outcome",
        "primary_failure_mode",
        "failure_modes",
        "confidence",
        "reasoning",
    ],
    "additionalProperties": False,
}


TASK_SCHEMAS = {
    "binary_success": {
        "name": "binary_success",
        "schema": BINARY_SUCCESS_SCHEMA,
    },
    "failure_mode_classification": {
        "name": "failure_mode_classification",
        "schema": FAILURE_MODE_CLASSIFICATION_SCHEMA,
    },
    "single_choice_multiclass": {
        "name": "single_choice_multiclass",
        "schema": SINGLE_CHOICE_MULTICLASS_SCHEMA,
    },
}
