from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import requests

from .schemas import TASK_SCHEMAS


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def data_url(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type is None:
        mime_type = "video/mp4"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_response_format(task_name: str) -> dict[str, Any]:
    task_schema = TASK_SCHEMAS[task_name]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": task_schema["name"],
            "strict": True,
            "schema": task_schema["schema"],
        },
    }


def build_messages(
    prompt_text: str,
    media_items: list[dict[str, Any]],
    *,
    encode_media: bool = True,
    media_input_type: str = "video",
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt_text}]
    for index, media in enumerate(media_items, start=1):
        item_label = "Contact sheet" if media_input_type == "image_contact_sheet" else "Video"
        content.append(
            {
                "type": "text",
                "text": (
                    f"{item_label} {index}: file_name={media['file_name']}, "
                    f"camera_view={media['camera_view']}, "
                    f"camera_device={media.get('camera_device') or 'unknown'}."
                ),
            }
        )
        if media_input_type == "image_contact_sheet":
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_url(media["path"])
                        if encode_media
                        else f"data:image/jpeg;base64,<dry-run: {media['path']}>",
                    },
                }
            )
            continue
        content.append(
            {
                "type": "video_url",
                "video_url": {
                    "url": data_url(media["path"])
                    if encode_media
                    else f"data:video/mp4;base64,<dry-run: {media['path']}>",
                },
            }
        )
    return [
        {
            "role": "system",
            "content": (
                "You are a careful lab automation evaluator. "
                "Judge only from visible evidence in the provided video inputs."
            ),
        },
        {"role": "user", "content": content},
    ]


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = json.loads(json.dumps(payload))
    for message in redacted.get("messages", []):
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if item.get("type") in {"video_url", "image_url"}:
                media_url = (
                    item.get("video_url")
                    or item.get("videoUrl")
                    or item.get("image_url")
                    or item.get("imageUrl")
                    or {}
                )
                url = media_url.get("url", "")
                if url.startswith("data:"):
                    prefix, _, encoded = url.partition(",")
                    media_url["url"] = f"{prefix},<base64 redacted: {len(encoded)} chars>"
    return redacted


class OpenRouterClient:
    def __init__(self, config: dict[str, Any]) -> None:
        self.api_url = config["api_url"]
        self.api_key_env = config.get("api_key_env", "OPENROUTER_API_KEY")
        self.timeout_seconds = config.get("timeout_seconds", 180)
        self.metadata_enabled = bool(config.get("metadata_enabled", True))

    def require_api_key(self) -> str:
        load_dotenv()
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Missing OpenRouter API key. Set {self.api_key_env} in the environment "
                "or in a local .env file before running."
            )
        return api_key

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.require_api_key()}",
            "Content-Type": "application/json",
        }
        if self.metadata_enabled:
            headers["X-OpenRouter-Metadata"] = "enabled"
        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_text": response.text}
        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenRouter request failed with {response.status_code}: {response_data}"
            )
        return response_data


def extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    return json.dumps(content)
