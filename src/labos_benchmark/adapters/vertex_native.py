"""Native Vertex AI adapter (REST generateContent) with explicit context caching.

Why this exists (probed 2026-08-08, docs/MODEL_ROSTER_AND_BUDGET.md §4):
Gemini's *implicit* caching only fires on byte-identical payloads, so the
3-prompt suite gains nothing from request ordering alone. *Explicit* context
caching does work across prompts: create one ``cachedContents`` holding the
media prefix per clip, then reference it from each prompt call — 99.9% of
input bills at the cached rate. Vertex's OpenAI-compatible endpoint exposes
neither ``cachedContents`` nor cached-token usage, hence this native adapter.

Auth: prefers a fresh ADC user token minted via
``gcloud auth application-default print-access-token`` (auto-refreshed, so
multi-hour runs survive the ~1h token expiry). A static ``VERTEX_ACCESS_TOKEN``
env var or ``api_key`` config overrides it (probes/CI), but will expire.

Usage mapping: usageMetadata -> the OpenAI-style keys client.py expects,
including ``prompt_tokens_details.cached_tokens``; Vertex returns no cost
field, so pricing comes from config/model_costs.json (source "table").
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import requests

from .base import AdapterResult, BaseVLMAdapter

_TOKEN_LIFETIME_S = 45 * 60  # ADC tokens last ~60 min; re-mint well before that


class VertexNativeAdapter(BaseVLMAdapter):
    adapter_name = "vertex_native"

    def __init__(self, model_config: dict[str, Any]) -> None:
        super().__init__(model_config)
        self.project = model_config.get("project") or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self.location = model_config.get("location", "global")
        self.timeout = int(model_config.get("timeout_s", 300))
        if not self.project:
            raise ValueError("vertex_native needs `project` in the model config "
                             "or GOOGLE_CLOUD_PROJECT in the environment")
        self._token: str | None = None
        self._token_expiry = 0.0
        self._token_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Auth
    # ------------------------------------------------------------------ #
    def _mint_token(self) -> str:
        static = self.model_config.get("api_key") or os.environ.get(
            self.model_config.get("api_key_env", "") or "VERTEX_ACCESS_TOKEN"
        )
        if static:
            return static
        proc = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "could not mint a Vertex token: set VERTEX_ACCESS_TOKEN or run "
                f"`gcloud auth application-default login` ({proc.stderr.strip()[:200]})"
            )
        return proc.stdout.strip()

    def _headers(self, *, force_refresh: bool = False) -> dict[str, str]:
        with self._token_lock:
            if force_refresh or self._token is None or time.time() >= self._token_expiry:
                self._token = self._mint_token()
                self._token_expiry = time.time() + _TOKEN_LIFETIME_S
            token = self._token
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _post(self, url: str, payload: dict[str, Any]) -> requests.Response:
        response = requests.post(url, headers=self._headers(), data=json.dumps(payload),
                                 timeout=self.timeout)
        if response.status_code == 401:  # token expired mid-run: re-mint once
            response = requests.post(url, headers=self._headers(force_refresh=True),
                                     data=json.dumps(payload), timeout=self.timeout)
        response.raise_for_status()
        return response

    # ------------------------------------------------------------------ #
    # Request building
    # ------------------------------------------------------------------ #
    @property
    def _base(self) -> str:
        host = ("aiplatform.googleapis.com" if self.location == "global"
                else f"{self.location}-aiplatform.googleapis.com")
        return (f"https://{host}/v1/projects/{self.project}/locations/{self.location}")

    @property
    def _model_path(self) -> str:
        model = self.provider_model_id or self.model_id
        return f"publishers/google/models/{model}"

    def _media_parts(self, media: list[dict[str, Any]]) -> list[dict[str, Any]]:
        parts: list[dict[str, Any]] = []
        for item in media:
            if item["type"] not in {"image", "video"}:
                raise ValueError(f"Unsupported vertex_native media type: {item['type']}")
            if item.get("label"):
                parts.append({"text": str(item["label"])})
            path = item["path"]
            mime_type = mimetypes.guess_type(path)[0] or (
                "video/mp4" if item["type"] == "video" else "image/jpeg"
            )
            data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
            parts.append({"inline_data": {"mime_type": mime_type, "data": data}})
        return parts

    def _generation_config(self, response_format: dict[str, Any] | None) -> dict[str, Any]:
        config: dict[str, Any] = {}
        if self.model_config.get("temperature") is not None:
            config["temperature"] = self.model_config["temperature"]
        for key in ("max_tokens", "max_completion_tokens"):
            if self.model_config.get(key) is not None:
                config["maxOutputTokens"] = self.model_config[key]
        if response_format is not None:
            config["responseMimeType"] = "application/json"
            config["responseSchema"] = response_format["json_schema"]["schema"]
        if self.model_config.get("thinking_budget") is not None:
            config["thinkingConfig"] = {"thinkingBudget": int(self.model_config["thinking_budget"])}
        return config

    @staticmethod
    def _usage_from_metadata(um: dict[str, Any]) -> dict[str, Any]:
        # thoughts bill as output tokens, so fold them into completion_tokens
        completion = int(um.get("candidatesTokenCount", 0)) + int(um.get("thoughtsTokenCount", 0))
        usage = {
            "prompt_tokens": int(um.get("promptTokenCount", 0)),
            "completion_tokens": completion,
            "total_tokens": int(um.get("totalTokenCount", 0)),
            "prompt_tokens_details": {
                "cached_tokens": int(um.get("cachedContentTokenCount", 0)),
            },
        }
        return usage

    # ------------------------------------------------------------------ #
    # Explicit context caching
    # ------------------------------------------------------------------ #
    def create_cache(self, media: list[dict[str, Any]],
                     *, ttl_s: int = 300) -> tuple[str, dict[str, Any]]:
        """Store the media prefix as a cachedContents resource.

        Returns (resource_name, usage): every subsequent
        generate(cached_content=name) bills these tokens at the cached rate,
        but the write itself bills them once at the standard input rate —
        `usage` carries that count so the caller can put it in the cost ledger
        (storage is excluded: negligible at short TTLs). TTL bounds storage
        cost; the resource may also be deleted eagerly with delete_cache().
        """
        payload = {
            "model": f"projects/{self.project}/locations/{self.location}/{self._model_path}",
            "contents": [{"role": "user", "parts": self._media_parts(media)}],
            "ttl": f"{int(ttl_s)}s",
        }
        response = self._post(f"{self._base}/cachedContents", payload)
        body = response.json()
        total = int((body.get("usageMetadata") or {}).get("totalTokenCount", 0))
        usage = {"prompt_tokens": total, "completion_tokens": 0, "total_tokens": total}
        return body["name"], usage

    def delete_cache(self, cache_name: str) -> None:
        """Best-effort eager delete (TTL is the safety net)."""
        host = self._base.split("/v1/")[0]
        try:
            requests.delete(f"{host}/v1/{cache_name}", headers=self._headers(), timeout=60)
        except Exception:  # noqa: BLE001 — TTL will expire the cache anyway
            pass

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    def generate(
        self,
        *,
        prompt: str,
        media: list[dict[str, Any]],
        request_metadata: dict[str, Any],
        response_format: dict[str, Any] | None = None,
        cached_content: str | None = None,
    ) -> AdapterResult:
        parts: list[dict[str, Any]] = []
        if cached_content is None:
            parts.extend(self._media_parts(media))
        elif media:
            raise ValueError("pass media via create_cache() when using cached_content")
        parts.append({"text": prompt})
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": self._generation_config(response_format),
        }
        if cached_content is not None:
            payload["cachedContent"] = cached_content

        start = time.perf_counter()
        response = self._post(f"{self._base}/{self._model_path}:generateContent", payload)
        latency_s = time.perf_counter() - start
        body = response.json()
        candidates = body.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        raw_text = "".join(
            part.get("text", "")
            for part in candidate.get("content", {}).get("parts", [])
        )
        return AdapterResult(
            raw_text=raw_text,
            usage=self._usage_from_metadata(body.get("usageMetadata", {})),
            provider_response={"response": body, "request_metadata": request_metadata},
            finish_reason=candidate.get("finishReason"),
            latency_s=latency_s,
        )
