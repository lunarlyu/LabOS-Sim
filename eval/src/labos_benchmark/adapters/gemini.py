from __future__ import annotations

import mimetypes
import os
import time
from typing import Any

from .base import AdapterResult, BaseVLMAdapter
from .openai_compatible import OpenAICompatibleAdapter


class GeminiAdapter(BaseVLMAdapter):
    """Gemini adapter boundary.

    Inspired by VLMEvalKit's Gemini wrapper. The configured default target is
    `gemini-3.1-pro` / OpenRouter `google/gemini-3.1-pro-preview`.
    """

    adapter_name = "gemini"

    def __init__(self, model_config: dict[str, Any]) -> None:
        super().__init__(model_config)
        self.api_style = model_config.get("api_style", "google_genai")
        self._openai_compatible = OpenAICompatibleAdapter(model_config)

    def generate(
        self,
        *,
        prompt: str,
        media: list[dict[str, Any]],
        request_metadata: dict[str, Any],
        response_format: dict[str, Any] | None = None,
    ) -> AdapterResult:
        if self.api_style == "openai_compatible":
            return self._openai_compatible.generate(
                prompt=prompt,
                media=media,
                request_metadata=request_metadata,
                response_format=response_format,
            )

        from google import genai
        from google.genai import types

        api_key = self.model_config.get("api_key")
        if api_key is None and self.model_config.get("api_key_env"):
            api_key = os.environ.get(self.model_config["api_key_env"])
        client = genai.Client(api_key=api_key)
        contents: list[Any] = []
        for item in media:
            if item["type"] not in {"image", "video"}:
                raise ValueError(f"Unsupported Gemini media type: {item['type']}")
            if item.get("label"):
                contents.append(str(item["label"]))
            uploaded = client.files.upload(file=item["path"])
            while True:
                uploaded = client.files.get(name=uploaded.name)
                if uploaded.state == "ACTIVE":
                    break
                time.sleep(2)
            mime_type = mimetypes.guess_type(item["path"])[0]
            if item["type"] == "video":
                mime_type = mime_type or "video/mp4"
            else:
                mime_type = mime_type or "image/jpeg"
            part = types.Part.from_uri(file_uri=uploaded.uri, mime_type=mime_type)
            fps = self.model_config.get("fps")
            if item["type"] == "video" and fps:
                part.video_metadata = types.VideoMetadata(fps=float(fps))
            contents.append(part)
        contents.append(prompt)

        config_args: dict[str, Any] = {}
        for key, target in (
            ("temperature", "temperature"),
            ("max_tokens", "max_output_tokens"),
            ("max_completion_tokens", "max_output_tokens"),
        ):
            if self.model_config.get(key) is not None:
                config_args[target] = self.model_config[key]
        if response_format is not None:
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = response_format["json_schema"]["schema"]
        if self.model_config.get("thinking_budget") is not None:
            config_args["thinking_config"] = types.ThinkingConfig(
                thinking_budget=int(self.model_config["thinking_budget"])
            )
        start = time.perf_counter()
        response = client.models.generate_content(
            model=self.model_id or self.provider_model_id,
            contents=contents,
            config=types.GenerateContentConfig(**config_args),
        )
        latency_s = time.perf_counter() - start
        return AdapterResult(
            raw_text=response.text or "",
            provider_response={"response": str(response), "request_metadata": request_metadata},
            latency_s=latency_s,
        )
