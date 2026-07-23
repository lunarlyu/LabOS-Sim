from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterResult:
    """Uniform return type for every provider adapter.

    `usage` carries the provider's raw usage block (token counts and, for
    OpenRouter, a `cost` field). `cost_usd` is filled by the client layer; it is
    left None by adapters so pricing stays transport-agnostic.
    """

    raw_text: str
    parsed: dict[str, Any] | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    provider_response: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None
    latency_s: float | None = None
    cost_usd: float | None = None


class BaseVLMAdapter:
    """Shared adapter boundary for LabOS-Sim model calls (VLM or text LLM).

    Subclasses implement `generate()` for one provider. `media` is a list of
    {"type": "video"|"image", "path": str} items (empty for text-only LLM calls,
    e.g. the p6 parser).
    """

    adapter_name = "base"

    def __init__(self, model_config: dict[str, Any]) -> None:
        self.model_config = model_config
        self.model_id = model_config.get("model_id")
        self.provider_model_id = model_config.get("provider_model_id")

    def generate(
        self,
        *,
        prompt: str,
        media: list[dict[str, Any]],
        request_metadata: dict[str, Any],
        response_format: dict[str, Any] | None = None,
    ) -> AdapterResult:
        raise NotImplementedError
