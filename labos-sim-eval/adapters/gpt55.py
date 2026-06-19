from __future__ import annotations

from typing import Any

from .openai_compatible import OpenAICompatibleAdapter


class GPT55Adapter(OpenAICompatibleAdapter):
    """GPT-5.5 adapter boundary.

    Inspired by VLMEvalKit's GPT API wrapper. The configured default target is
    `gpt-5.5-2026-04-23` / OpenRouter `openai/gpt-5.5`.
    """

    adapter_name = "gpt55"
