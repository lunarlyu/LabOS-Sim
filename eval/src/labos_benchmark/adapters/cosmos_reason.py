from __future__ import annotations

from typing import Any

from .openai_compatible import OpenAICompatibleAdapter


class CosmosReasonAdapter(OpenAICompatibleAdapter):
    """Cosmos Reason adapter boundary.

    Intended for NVIDIA Cosmos 3 Reasoner served locally through vLLM or NIM.
    The current NVIDIA/Cosmos repo exposes an OpenAI-compatible chat endpoint
    for Reasoner, with video sampling controlled through `media_io_kwargs`.
    """

    adapter_name = "cosmos_reason"
