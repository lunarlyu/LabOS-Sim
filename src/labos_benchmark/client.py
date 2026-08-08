"""Unified call layer: retry/backoff + cost & token accounting over any adapter.

Adapted from the brdm project's ``llm.py`` (the LLMOutput / LLMCallMetrics
pattern), made transport-agnostic: it wraps an ``adapters.BaseVLMAdapter`` rather
than calling a provider SDK directly, so the same accounting covers VLM (p1-p3)
and text-LLM (p6) calls.

Pricing is hybrid (see docs/ARCHITECTURE.md):
  1. provider-reported ``usage["cost"]`` (OpenRouter)         -> source "provider"
  2. tokens x config/model_costs.json rates                   -> source "table"
  3. otherwise 0.0, but raw token counts are still recorded   -> source "none"
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .adapters import AdapterResult, BaseVLMAdapter


# --------------------------------------------------------------------------- #
# Cost configuration
# --------------------------------------------------------------------------- #
def load_model_costs(path: str | Path = "config/model_costs.json") -> dict[str, dict]:
    p = Path(path)
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _tokens(usage: dict[str, Any]) -> tuple[int, int]:
    in_tok = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    out_tok = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    return int(in_tok), int(out_tok)


def _cached_tokens(usage: dict[str, Any]) -> int:
    details = usage.get("prompt_tokens_details") or {}
    return int(details.get("cached_tokens") or usage.get("cache_read_input_tokens") or 0)


def compute_cost(usage: dict[str, Any] | None, cost_entry: dict | None) -> tuple[float, str]:
    """Return (total_usd, source) for one call's usage block.

    Cached prompt tokens (context caching / prompt caching) bill at
    ``cached_input_cost_per_1M`` when the table provides it; they are a subset
    of prompt_tokens, so the uncached remainder bills at the normal input rate.
    """
    usage = usage or {}
    provider = usage.get("cost")
    if provider is not None:
        return float(provider), "provider"
    if cost_entry:
        in_tok, out_tok = _tokens(usage)
        cached = min(_cached_tokens(usage), in_tok)
        cached_rate = cost_entry.get("cached_input_cost_per_1M")
        if not cached or cached_rate is None:
            cached, cached_rate = 0, 0.0
        cost = (
            cost_entry.get("input_cost_per_1M", 0.0) * (in_tok - cached) / 1e6
            + cached_rate * cached / 1e6
            + cost_entry.get("output_cost_per_1M", 0.0) * out_tok / 1e6
        )
        return float(cost), "table"
    return 0.0, "none"


# --------------------------------------------------------------------------- #
# Per-call accumulator + flat metrics row
# --------------------------------------------------------------------------- #
@dataclass
class CallResult:
    """Accumulates output, tokens and cost across retries for one logical call."""

    output: Any = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    cost_source: str = "none"
    num_retries: int = 0
    success: bool | None = None
    raw_outputs_per_try: list = field(default_factory=list)

    @classmethod
    def blank(cls) -> "CallResult":
        return cls()

    def total_cost(self) -> float:
        return self.cost

    def register_attempt(self, *, output: Any, input_tokens: int, output_tokens: int,
                         cost: float, cost_source: str, success: bool,
                         raw_output: str | None = None) -> None:
        self.output = output
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost += cost
        if cost_source != "none":
            self.cost_source = cost_source
        self.num_retries += 1
        self.success = success
        self.raw_outputs_per_try.append(raw_output if raw_output is not None else output)

    def register_error(self) -> None:
        self.num_retries += 1
        self.success = False


@dataclass
class CallMetrics:
    """Flat, serializable cost-ledger row (one per logical call)."""

    input_tokens: int
    output_tokens: int
    cost: float
    cost_source: str
    num_retries: int
    success: bool | None
    timestamp: float
    runtime_s: float
    run_id: str
    model: str

    @classmethod
    def build(cls, result: CallResult, *, model: str, run_id: str, runtime_s: float) -> "CallMetrics":
        return cls(
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost=result.total_cost(),
            cost_source=result.cost_source,
            num_retries=result.num_retries,
            success=result.success,
            timestamp=time.time(),
            runtime_s=runtime_s,
            run_id=run_id,
            model=model,
        )


# --------------------------------------------------------------------------- #
# JSON extraction + retrying call wrapper
# --------------------------------------------------------------------------- #
def extract_jsons(text: str) -> list[str]:
    """Yield every top-level JSON object substring (robust to chatty models)."""
    decoder = json.JSONDecoder()
    results, i, n = [], 0, len(text or "")
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        try:
            _, end = decoder.raw_decode(text, i)
            results.append(text[i:end])
        except Exception:
            pass
        i += 1
    return results


def parse_first_json(text: str) -> dict | None:
    for chunk in extract_jsons(text):
        try:
            obj = json.loads(chunk)
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _backoff_sleep(try_i: int) -> None:
    time.sleep(min(15.0, 1.5 * (2 ** try_i) + random.random()))


def _http_status(exc: Exception) -> int | None:
    """Best-effort status extraction across requests/openai/httpx errors."""
    status = getattr(exc, "status_code", None)
    if status is not None:
        return int(status)
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return int(status) if status is not None else None


def call_with_retries(
    adapter: BaseVLMAdapter,
    *,
    prompt: str,
    media: list[dict[str, Any]],
    request_metadata: dict[str, Any],
    model_name: str,
    cost_entry: dict | None = None,
    max_retries: int = 5,
    parse_fn: Callable[[str], Any] | None = parse_first_json,
    response_format: dict[str, Any] | None = None,
    cached_content: str | None = None,
) -> tuple[CallResult, AdapterResult | None]:
    """Call an adapter with retries, accumulating cost into a CallResult.

    ``parse_fn`` turns raw text into structured output; success = non-None parse.
    Pass ``parse_fn=None`` to accept raw text.
    ``cached_content`` names a provider-side context cache holding the media
    prefix (adapters that support one, e.g. vertex_native.create_cache).
    Returns (CallResult, last AdapterResult).
    """
    result = CallResult.blank()
    last: AdapterResult | None = None
    for attempt in range(max_retries + 1):
        try:
            ar = adapter.generate(
                prompt=prompt,
                media=media,
                request_metadata=request_metadata,
                response_format=response_format,
                **({"cached_content": cached_content} if cached_content else {}),
            )
            last = ar
            cost, source = compute_cost(ar.usage, cost_entry)
            in_tok, out_tok = _tokens(ar.usage or {})
            parsed = parse_fn(ar.raw_text) if parse_fn else ar.raw_text
            success = bool(ar.raw_text) and (parsed is not None)
            result.register_attempt(
                output=parsed, input_tokens=in_tok, output_tokens=out_tok,
                cost=cost, cost_source=source, success=success, raw_output=ar.raw_text,
            )
            if success:
                return result, ar
        except Exception as exc:  # noqa: BLE001
            print(f"[WARNING] call failed (attempt {attempt + 1}/{max_retries + 1}): {exc}", flush=True)
            result.register_error()
            status = _http_status(exc)
            if status == 413:
                print("[WARNING] HTTP 413 is not retryable; reduce media payload size.", flush=True)
                break
            if cached_content and status in (400, 403, 404):
                # the context cache is likely expired/invalid — retrying the same
                # reference cannot succeed; let the caller fall back uncached
                print(f"[WARNING] HTTP {status} while referencing a context cache; "
                      "not retrying with the cache.", flush=True)
                break
        if attempt < max_retries:
            _backoff_sleep(attempt)
    return result, last
