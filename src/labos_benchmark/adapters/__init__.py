from __future__ import annotations

from typing import Any

from .base import AdapterResult, BaseVLMAdapter


def get_adapter(adapter_name: str, model_config: dict[str, Any]) -> BaseVLMAdapter:
    if adapter_name == "openai_compatible":
        from .openai_compatible import OpenAICompatibleAdapter

        return OpenAICompatibleAdapter(model_config)
    if adapter_name == "gemini":
        from .gemini import GeminiAdapter

        return GeminiAdapter(model_config)
    if adapter_name == "cosmos_reason":
        from .cosmos_reason import CosmosReasonAdapter

        return CosmosReasonAdapter(model_config)
    raise ValueError(f"Unknown adapter: {adapter_name}")


__all__ = ["AdapterResult", "BaseVLMAdapter", "get_adapter"]
