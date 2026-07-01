"""Shared collection loop used by every scripts/data_collection/run_*.py.

Two modes, dispatched by prompt_type:
  * VLM tasks (closed_binary / open_detection / multilabel_classification):
        iterate dataset samples, send video + prompt to a VLM.
  * parser tasks (p5/p6): iterate a prior p3/p4 run's outputs, fill the parser
        prompt, send text to an LLM.

Outputs go to runs/raw/{run_id}/{task}/{vlm}[/{llm}]/ with predictions.jsonl,
metrics.jsonl, run_config.json and per-call artifacts. The run_id (e.g. test_01,
full_01) groups everything from one run; the datapoints to run come from a
--data run_list.jsonl. See docs/ARCHITECTURE.md.

NOTE: this is the scaffold wiring. The provider adapters and dataset/media
helpers are borrowed from the previous codebase; the seams marked TODO are where
live-run details (contact-sheet media, p2-source selection) may need tuning once
data collection is exercised end to end.
"""
from __future__ import annotations

import dataclasses
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from . import client as _client
from . import prompts as _prompts
from . import schemas as _schemas
from .adapters import get_adapter
from .io_utils import append_jsonl, atomic_write_json, safe_name, setup_keys


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def _load_yaml(path: str | Path) -> dict:
    import yaml  # local import so importing the package doesn't require pyyaml

    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def load_config(
    models_path: str | Path = "config/models.yaml",
    defaults_path: str | Path = "config/defaults.yaml",
    costs_path: str | Path = "config/model_costs.json",
) -> dict:
    setup_keys()  # load API keys from _env.json into os.environ (no-op if absent)
    models = _load_yaml(models_path).get("models", {})
    defaults = _load_yaml(defaults_path)
    costs = _client.load_model_costs(costs_path)
    return {"models": models, "defaults": defaults, "model_costs": costs}


def _model_cfg_with_call_defaults(model_cfg: dict, call_cfg: dict) -> dict:
    """Apply run-level call defaults without overriding per-model settings."""
    out = dict(model_cfg)
    if "timeout_s" not in out and call_cfg.get("timeout_seconds") is not None:
        out["timeout_s"] = call_cfg["timeout_seconds"]
    if (
        "max_completion_tokens" not in out
        and "max_tokens" not in out
        and call_cfg.get("max_completion_tokens") is not None
    ):
        out["max_completion_tokens"] = call_cfg["max_completion_tokens"]
    return out


def _schema_request_for_task(task: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "provider_format": "json_schema",
        "response_format": _schemas.response_format_for_task(task),
    }


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _new_run_dir(run_id: str, task: str, *parts: str, runs_root: str | Path = "runs") -> Path:
    """runs/raw/{run_id}/{task}/{parts...}/ — run_id groups a whole run."""
    d = Path(runs_root) / "raw" / safe_name(run_id) / task
    for p in parts:
        d = d / safe_name(p)
    (d / "artifacts").mkdir(parents=True, exist_ok=True)
    return d


def _run_pool(fn: Callable, items: Iterable, concurrency: int) -> None:
    """Map fn over items, optionally in parallel (API calls are I/O-bound)."""
    items = list(items)
    if concurrency and concurrency > 1:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            list(ex.map(fn, items))
    else:
        for it in items:
            fn(it)


# --------------------------------------------------------------------------- #
# VLM collection (p1 / p2 / p3)
# --------------------------------------------------------------------------- #
def collect(
    task: str,
    model_name: str,
    config: dict,
    *,
    run_id: str,
    data_list: str | Path,
    camera_views: list[str] | None = None,
    limit: int | None = None,
    concurrency: int = 1,
    runs_root: str | Path = "runs",
    data_root: str | Path = "data",
) -> Path:
    """Collect one VLM's answers for a task: for each clip, one call with its angles.

    A DataPoint is one clip; ``resolve_videos`` returns its (up to 5) camera-angle
    videos, which are sent together in a single request -> one answer per clip.
    Clips come from ``data_list`` (a run_list.jsonl) and are processed with a
    thread pool of size ``concurrency``.
    """
    from .dataset import load_datapoints
    from .media import maybe_transcode_videos

    ptype = _prompts.prompt_type_of(task)
    if _prompts.is_parser(ptype):
        raise ValueError(f"Use run_parser() for parser task {task!r}.")

    defaults = config["defaults"]
    media_cfg = defaults.get("media", {})
    call_cfg = defaults.get("call", {})
    model_cfg = _model_cfg_with_call_defaults(config["models"][model_name], call_cfg)
    adapter = get_adapter(model_cfg["adapter"], model_cfg)
    cost_entry = config["model_costs"].get(model_cfg.get("provider_model_id"))
    cams = camera_views if camera_views is not None else media_cfg.get("camera_views", [])
    max_videos = int(media_cfg.get("max_videos_per_sample", 0) or 0)
    schema_request = _schema_request_for_task(task)

    prompt_text = _prompts.load_prompt(task)  # protocol is baked into the .md
    parse_fn = _client.parse_first_json       # JSON for all tasks (p2 is still JSON-shaped)

    points = load_datapoints(data_list)
    if limit:
        points = points[:limit]

    run_dir = _new_run_dir(run_id, task, model_name, runs_root=runs_root)
    atomic_write_json(run_dir / "run_config.json",
                      {"run_id": run_id, "task": task, "model": model_name, "model_cfg": model_cfg,
                       "data_list": str(data_list), "data_root": str(data_root),
                       "camera_views": cams, "max_videos_per_sample": max_videos,
                       "concurrency": concurrency, "schema_request": schema_request,
                       "defaults": defaults})

    write_lock = threading.Lock()

    def _process(dp) -> None:
        videos = dp.resolve_videos(data_root, cams or None)
        if max_videos > 0:
            videos = videos[:max_videos]
        videos = maybe_transcode_videos(videos, run_dir / "media_cache" / dp.sample_id, media_cfg)
        media_type = "image" if media_cfg.get("input_type") == "image_contact_sheet" else "video"
        media = [{"type": media_type, "path": str(v["path"])} for v in videos]
        result, ar = _client.call_with_retries(
            adapter, prompt=prompt_text, media=media,
            request_metadata={"task": task, "model": model_name,
                              "sample_id": dp.sample_id, "index": dp.index},
            model_name=model_name, cost_entry=cost_entry,
            max_retries=int(call_cfg.get("max_retries", 5)), parse_fn=parse_fn,
            response_format=schema_request["response_format"],
        )
        with write_lock:
            _write_record(run_dir, run_id, task, model_name, dp.sample_id, result, ar,
                          expected=dp.expected)

    _run_pool(_process, points, concurrency)
    print(f"[done] {run_id} / {task} / {model_name}: {len(points)} clips -> {run_dir}")
    return run_dir


# --------------------------------------------------------------------------- #
# p6 parser (text LLM over a prior p2 run)
# --------------------------------------------------------------------------- #
def run_parser(
    task: str,
    llm_name: str,
    source_run_dir: str | Path,
    config: dict,
    *,
    run_id: str | None = None,
    concurrency: int = 1,
    runs_root: str | Path = "runs",
) -> Path:
    """Fill a parser prompt from each source VLM prediction and call a text LLM.

    source_run_dir is runs/raw/{run_id}/{op}_open_detection_{strict|free}/{vlm}.
    The parser output goes under the same run_id at
    {run_id}/{op}_open_detection_{strict|free}_parser/{vlm}/{llm}/. The source
    prediction's fields (outcome, observed_errors OR description, confidence) are
    filled into the parser prompt's {{...}} placeholders by name; `reasoning` is
    never passed.
    """
    if not _prompts.is_parser(_prompts.prompt_type_of(task)):
        raise ValueError(f"run_parser expects a *_parser task, got {task!r}")

    source_run_dir = Path(source_run_dir)
    vlm_name = source_run_dir.name             # {vlm}
    if run_id is None:
        run_id = source_run_dir.parent.parent.name  # raw/{run_id}/{src_task}/{vlm}
    call_cfg = config["defaults"].get("call", {})
    model_cfg = _model_cfg_with_call_defaults(config["models"][llm_name], call_cfg)
    adapter = get_adapter(model_cfg["adapter"], model_cfg)
    cost_entry = config["model_costs"].get(model_cfg.get("provider_model_id"))
    template = _prompts.load_prompt_file(_prompts.get_prompt_path(task))
    schema_request = _schema_request_for_task(task)

    run_dir = _new_run_dir(run_id, task, vlm_name, llm_name, runs_root=runs_root)
    atomic_write_json(run_dir / "run_config.json",
                      {"run_id": run_id, "task": task, "vlm": vlm_name, "llm": llm_name,
                       "source_run_dir": str(source_run_dir), "model_cfg": model_cfg,
                       "schema_request": schema_request})

    rows = [json.loads(ln) for ln in
            (source_run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    write_lock = threading.Lock()

    def _process(row) -> None:
        src = row.get("prediction") or {}
        # Fill placeholders by field name from the source prediction (reasoning excluded).
        fill = {k: json.dumps(v) for k, v in src.items() if k != "reasoning"}
        prompt_text = _prompts.fill_in_prompt(template, fill)
        result, ar = _client.call_with_retries(
            adapter, prompt=prompt_text, media=[],
            request_metadata={"task": task, "vlm": vlm_name, "llm": llm_name,
                              "sample_id": row.get("sample_id")},
            model_name=llm_name, cost_entry=cost_entry,
            max_retries=int(call_cfg.get("max_retries", 5)), parse_fn=_client.parse_first_json,
            response_format=schema_request["response_format"],
        )
        with write_lock:
            _write_record(run_dir, run_id, task, vlm_name, row.get("sample_id"), result, ar,
                          expected=row.get("expected"), metrics_model=llm_name,
                          extra={"source_vlm": vlm_name, "parser_llm": llm_name})

    _run_pool(_process, rows, concurrency)
    print(f"[done] {run_id} / {task}: parsed {source_run_dir} with {llm_name} ({len(rows)} rows) -> {run_dir}")
    return run_dir


# --------------------------------------------------------------------------- #
# Shared record writer
# --------------------------------------------------------------------------- #
def _write_record(run_dir: Path, run_id: str, task: str, model_name: str, sample_id: str,
                  result: _client.CallResult, ar, *, expected: dict | None = None,
                  metrics_model: str | None = None, extra: dict | None = None) -> None:
    runtime = ar.latency_s if ar is not None else 0.0
    metrics = _client.CallMetrics.build(result, model=metrics_model or model_name, run_id=run_id,
                                        runtime_s=runtime or 0.0)
    artifact_id = safe_name(f"{model_name}__{sample_id}")
    if ar is not None:
        atomic_write_json(run_dir / "artifacts" / f"{artifact_id}.json",
                          {"raw_text": ar.raw_text, "usage": ar.usage,
                           "finish_reason": ar.finish_reason})
    record = {
        "run_id": run_id, "task": task, "model": model_name, "sample_id": sample_id,
        "prediction": result.output if result.success else None,
        "success": result.success,
        "raw_output": result.raw_outputs_per_try[-1] if result.raw_outputs_per_try else None,
    }
    if expected is not None:
        record["expected"] = expected
    if extra:
        record.update(extra)
    append_jsonl(run_dir / "predictions.jsonl", record)
    append_jsonl(run_dir / "metrics.jsonl", dataclasses.asdict(metrics))
