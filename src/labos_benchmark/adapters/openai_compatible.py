from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import requests

from .base import AdapterResult, BaseVLMAdapter


def _read_env(name: str | None, default: str | None = None) -> str | None:
    if not name:
        return default
    return os.environ.get(name, default)


def _data_uri(path: str) -> str:
    media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{data}"


def _file_uri(path: str) -> str:
    return Path(path).resolve().as_uri()


class OpenAICompatibleAdapter(BaseVLMAdapter):
    """Shared transport for OpenAI-compatible hosted or local VLM endpoints."""

    adapter_name = "openai_compatible"

    def __init__(self, model_config: dict[str, Any]) -> None:
        super().__init__(model_config)
        self.base_url = model_config.get("base_url") or os.environ.get(
            model_config.get("base_url_env", ""),
            "https://openrouter.ai/api/v1",
        )
        self.api_key = model_config.get("api_key") or _read_env(
            model_config.get("api_key_env"),
            model_config.get("api_key_default", ""),
        )
        self.timeout = int(model_config.get("timeout_s", 300))

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.model_config.get("http_referer"):
            headers["HTTP-Referer"] = self.model_config["http_referer"]
        if self.model_config.get("app_title"):
            headers["X-Title"] = self.model_config["app_title"]
        return headers

    def _media_block(self, item: dict[str, Any]) -> dict[str, Any]:
        transport = self.model_config.get("media_transport", "file_uri")
        path = item["path"]
        if item["type"] == "image":
            url = _data_uri(path) if transport == "data_uri" else _file_uri(path)
            return {"type": "image_url", "image_url": {"url": url}}
        if item["type"] == "video":
            url = _data_uri(path) if transport == "data_uri" else _file_uri(path)
            return {"type": "video_url", "video_url": {"url": url}}
        raise ValueError(f"Unsupported media type for OpenAI-compatible transport: {item['type']}")

    def build_payload(
        self,
        *,
        prompt: str,
        media: list[dict[str, Any]],
        request_metadata: dict[str, Any],
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = []
        for item in media:
            if item.get("label"):
                content.append({"type": "text", "text": str(item["label"])})
            content.append(self._media_block(item))
        if content and self.model_config.get("anthropic_cache_control"):
            # Anthropic prompt caching (passed through by OpenRouter): a
            # breakpoint on the last media block caches the whole media prefix,
            # so back-to-back calls for the same clip (collect_suite) re-bill
            # it at the cached-read rate while the trailing task prompt varies.
            content[-1]["cache_control"] = {"type": "ephemeral"}
        content.append({"type": "text", "text": prompt})
        messages: list[dict[str, Any]] = []
        system_prompt = self.model_config.get("system_prompt")
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        payload: dict[str, Any] = {
            "model": self.provider_model_id or self.model_id,
            "messages": messages,
            "stream": False,
            "metadata": request_metadata,
        }
        for key in ("temperature", "top_p", "max_tokens", "max_completion_tokens", "seed"):
            if key in self.model_config and self.model_config[key] is not None:
                payload[key] = self.model_config[key]
        if response_format is not None:
            payload["response_format"] = response_format
        if self.model_config.get("extra_body"):
            payload.update(self.model_config["extra_body"])
        return payload

    def generate(
        self,
        *,
        prompt: str,
        media: list[dict[str, Any]],
        request_metadata: dict[str, Any],
        response_format: dict[str, Any] | None = None,
    ) -> AdapterResult:
        payload = self.build_payload(
            prompt=prompt,
            media=media,
            request_metadata=request_metadata,
            response_format=response_format,
        )
        url = self.base_url.rstrip("/") + "/chat/completions"
        start = time.perf_counter()
        response = requests.post(url, headers=self._headers(), data=json.dumps(payload), timeout=self.timeout)
        latency_s = time.perf_counter() - start
        response.raise_for_status()
        provider_response = response.json()
        choice = provider_response["choices"][0]
        raw_text = choice.get("message", {}).get("content", "")
        return AdapterResult(
            raw_text=raw_text,
            usage=provider_response.get("usage") or {},
            provider_response=provider_response,
            finish_reason=choice.get("finish_reason"),
            latency_s=latency_s,
        )
