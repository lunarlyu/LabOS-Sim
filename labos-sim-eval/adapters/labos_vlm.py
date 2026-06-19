from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterResult:
    raw_text: str
    parsed: dict[str, Any] | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    provider_response: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None
    latency_s: float | None = None
    cost_usd: float | None = None


class BaseVLMAdapter:
    """Shared adapter boundary for LabOS-Sim VLM calls."""

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
    ) -> AdapterResult:
        raise NotImplementedError


def get_adapter(adapter_name: str, model_config: dict[str, Any]) -> BaseVLMAdapter:
    if adapter_name == "gpt55":
        from .gpt55 import GPT55Adapter

        return GPT55Adapter(model_config)
    if adapter_name == "claude_opus":
        from .claude_opus import ClaudeOpusAdapter

        return ClaudeOpusAdapter(model_config)
    if adapter_name == "gemini":
        from .gemini import GeminiAdapter

        return GeminiAdapter(model_config)
    if adapter_name == "qwen3vl":
        from .qwen3vl import Qwen3VLAdapter

        return Qwen3VLAdapter(model_config)
    if adapter_name == "cosmos_reason":
        from .cosmos_reason import CosmosReasonAdapter

        return CosmosReasonAdapter(model_config)
    raise ValueError(f"Unknown adapter: {adapter_name}")
