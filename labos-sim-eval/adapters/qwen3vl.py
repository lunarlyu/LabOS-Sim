from __future__ import annotations

from typing import Any

from .openai_compatible import OpenAICompatibleAdapter


class Qwen3VLAdapter(OpenAICompatibleAdapter):
    """Qwen3-VL adapter boundary.

    Intended to follow Qwen3-VL official cookbook defaults rather than bumped
    VLMEvalKit pixel settings.
    """

    adapter_name = "qwen3vl"
