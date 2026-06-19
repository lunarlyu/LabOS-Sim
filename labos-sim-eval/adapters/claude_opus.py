from __future__ import annotations

from typing import Any

from .openai_compatible import OpenAICompatibleAdapter


class ClaudeOpusAdapter(OpenAICompatibleAdapter):
    """Claude Opus adapter boundary.

    Inspired by VLMEvalKit's Claude wrapper. The configured default target is
    `claude-opus-4-8` / OpenRouter `anthropic/claude-opus-4.8`.
    """

    adapter_name = "claude_opus"
