"""Shared collection loop used by every scripts/data_collection/run_*.py.

Two modes, dispatched by prompt_type:
  * VLM tasks (closed_binary / open_detection / multilabel_classification):
        iterate dataset samples, send video + prompt to a VLM.
  * parser tasks (p5/p6): iterate a prior p3/p4 run's outputs, fill the parser
        prompt, send text to an LLM.

Outputs go to runs/raw/{run_id}/{task}/{vlm}[/{llm}]/ with predictions.jsonl,
metrics.jsonl and run_config.json (raw provider text + finish_reason live inline
in predictions.jsonl). Preprocessed media is content-addressed in a shared
runs/.media_cache/ so re-runs reuse transcodes instead of redoing ffmpeg. The
run_id (e.g. test_01, full_01) groups everything from one run; the datapoints to
run come from a --data run_list.jsonl. See docs/ARCHITECTURE.md.

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
    d.mkdir(parents=True, exist_ok=True)
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


def prediction_succeeded(row: dict) -> bool:
    """Return whether a prediction row is complete enough to score or resume from."""
    return row.get("success") is True and row.get("prediction") is not None


def _latest_rows(path: Path) -> dict[str, dict]:
    """Return the latest row per sample, preferring any successful retry."""
    if not path.is_file():
        return {}
    latest: dict[str, dict] = {}
    successful: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        sample_id = row.get("sample_id")
        if not sample_id:
            continue
        latest[sample_id] = row
        if prediction_succeeded(row):
            successful[sample_id] = row
    return {sample_id: successful.get(sample_id, row) for sample_id, row in latest.items()}


def successful_sample_ids(predictions: str | Path) -> set[str]:
    """Return unique sample IDs with a successful, non-null prediction."""
    return {
        sample_id for sample_id, row in _latest_rows(Path(predictions)).items()
        if prediction_succeeded(row)
    }


def _completed_sample_ids(run_dir: Path) -> set[str]:
    return successful_sample_ids(run_dir / "predictions.jsonl")


# --------------------------------------------------------------------------- #
# VLM collection (p1 / p2 / p3)
# --------------------------------------------------------------------------- #
def prepare_clip_media(dp, *, media_cfg: dict, cams: list[str], max_videos: int,
                       runs_root: str | Path, data_root: str | Path) -> list[dict[str, Any]]:
    """Resolve one clip's camera videos and preprocess them into media blocks.

    Preprocessing is content-addressed (runs/.media_cache/), so repeated calls
    for the same clip return byte-identical files in the same (camera) order —
    a requirement for provider-side prefix caching.
    """
    from .media import maybe_transcode_videos

    videos = dp.resolve_videos(data_root, cams or None)
    if max_videos > 0:
        videos = videos[:max_videos]
    videos = maybe_transcode_videos(videos, Path(runs_root) / ".media_cache", media_cfg)
    media_type = (
        "image"
        if media_cfg.get("input_type") in {"image_contact_sheet", "image_frames"}
        else "video"
    )
    return [
        {
            "type": media_type,
            "path": str(v["path"]),
            **({"label": v["label"]} if v.get("label") else {}),
        }
        for v in videos
    ]


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
    return collect_suite([task], model_name, config, run_id=run_id, data_list=data_list,
                         camera_views=camera_views, limit=limit, concurrency=concurrency,
                         runs_root=runs_root, data_root=data_root)[task]


def collect_suite(
    tasks: list[str],
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
) -> dict[str, Path]:
    """Collect several VLM tasks clip-grouped: each clip's tasks run back-to-back.

    Produces the same per-task run dirs, records and resume behavior as calling
    collect() once per task, but instead of one full dataset pass per task, all
    tasks for a clip are sent within seconds of each other so the shared media
    prefix can bill at a cached rate. Two mechanisms (probed 2026-08-08, see
    docs/MODEL_ROSTER_AND_BUDGET.md §4):

    * Explicit context caching — when the model config has
      ``context_cache: {enabled: true}`` and the adapter implements
      ``create_cache`` (vertex_native): the media prefix is uploaded once per
      clip as a provider-side cache and each task call references it instead of
      re-sending media. Guaranteed discount; falls back to full media if cache
      creation or a cached call fails.
    * Provider-side prompt caching — on OpenAI-compatible routes the identical
      request prefix lets automatic prefix caching (OpenAI) or ``cache_control``
      markers (Anthropic; see OpenAICompatibleAdapter) hit. Best-effort; verify
      a route with scripts/probe_prompt_cache.py.

    Tasks for one clip run sequentially inside one worker — a provider caches a
    prefix only after the first call finishes — while the thread pool
    parallelizes across clips.
    """
    from .dataset import load_datapoints

    if not tasks:
        raise ValueError("collect_suite needs at least one task")
    for task in tasks:
        if _prompts.is_parser(_prompts.prompt_type_of(task)):
            raise ValueError(f"Use run_parser() for parser task {task!r}.")

    defaults = config["defaults"]
    media_cfg = defaults.get("media", {})
    call_cfg = defaults.get("call", {})
    model_cfg = _model_cfg_with_call_defaults(config["models"][model_name], call_cfg)
    adapter = get_adapter(model_cfg["adapter"], model_cfg)
    cost_entry = config["model_costs"].get(model_cfg.get("provider_model_id"))
    cams = camera_views if camera_views is not None else media_cfg.get("camera_views", [])
    max_videos = int(media_cfg.get("max_videos_per_sample", 0) or 0)
    parse_fn = _client.parse_first_json  # JSON for all tasks (p2 is still JSON-shaped)

    points = load_datapoints(data_list)
    if limit:
        points = points[:limit]

    prompt_texts: dict[str, str] = {}   # protocol is baked into each task's .md
    schema_requests: dict[str, dict] = {}
    run_dirs: dict[str, Path] = {}
    completed: dict[str, set[str]] = {}
    for task in tasks:
        prompt_texts[task] = _prompts.load_prompt(task)
        schema_requests[task] = _schema_request_for_task(task)
        run_dir = _new_run_dir(run_id, task, model_name, runs_root=runs_root)
        run_config = {"run_id": run_id, "task": task, "model": model_name, "model_cfg": model_cfg,
                      "data_list": str(data_list), "data_root": str(data_root),
                      "camera_views": cams, "max_videos_per_sample": max_videos,
                      "concurrency": concurrency, "schema_request": schema_requests[task],
                      "defaults": defaults}
        if len(tasks) > 1:
            run_config["suite_tasks"] = list(tasks)
        atomic_write_json(run_dir / "run_config.json", run_config)
        run_dirs[task] = run_dir
        completed[task] = _completed_sample_ids(run_dir)

    write_lock = threading.Lock()
    newly_succeeded: dict[str, set[str]] = {task: set() for task in tasks}
    pending = [dp for dp in points
               if any(dp.sample_id not in completed[task] for task in tasks)]

    cache_cfg = model_cfg.get("context_cache") or {}
    use_context_cache = bool(cache_cfg.get("enabled")) and hasattr(adapter, "create_cache")
    cache_ttl_s = int(cache_cfg.get("ttl_s", 900))

    def _call(task: str, dp, media: list[dict], cache_name: str | None):
        return _client.call_with_retries(
            adapter, prompt=prompt_texts[task], media=media,
            request_metadata={"task": task, "model": model_name,
                              "sample_id": dp.sample_id, "index": dp.index},
            model_name=model_name, cost_entry=cost_entry,
            max_retries=int(call_cfg.get("max_retries", 5)), parse_fn=parse_fn,
            response_format=schema_requests[task]["response_format"],
            cached_content=cache_name,
        )

    def _process(dp) -> None:
        media = prepare_clip_media(dp, media_cfg=media_cfg, cams=cams, max_videos=max_videos,
                                   runs_root=runs_root, data_root=data_root)
        tasks_todo = [task for task in tasks if dp.sample_id not in completed[task]]
        cache_name = None
        if use_context_cache and media and len(tasks_todo) > 1:
            try:
                cache_name = adapter.create_cache(media, ttl_s=cache_ttl_s)
            except Exception as exc:  # noqa: BLE001 — cache is an optimization, not a dependency
                print(f"[WARNING] context cache creation failed for {dp.sample_id}: {exc}; "
                      "sending full media per call", flush=True)
        try:
            for task in tasks_todo:
                result, ar = _call(task, dp, [] if cache_name else media, cache_name)
                if not result.success and cache_name:
                    # cache may have expired mid-clip (TTL) — one uncached retry round
                    print(f"[WARNING] cached call failed for {dp.sample_id}/{task}; "
                          "retrying with full media", flush=True)
                    result, ar = _call(task, dp, media, None)
                with write_lock:
                    _write_record(run_dirs[task], run_id, task, model_name, dp.sample_id,
                                  result, ar, expected=dp.expected)
                    if result.success and result.output is not None:
                        newly_succeeded[task].add(dp.sample_id)
        finally:
            if cache_name:
                adapter.delete_cache(cache_name)

    _run_pool(_process, pending, concurrency)
    for task in tasks:
        n_success = len(completed[task] | newly_succeeded[task])
        if n_success == len(points):
            print(f"[done] {run_id} / {task} / {model_name}: "
                  f"{n_success}/{len(points)} clips -> {run_dirs[task]}")
        else:
            print(f"[incomplete] {run_id} / {task} / {model_name}: "
                  f"{n_success}/{len(points)} clips succeeded; rerun the same command to retry failures -> {run_dirs[task]}")
    return run_dirs


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

    rows = list(_latest_rows(source_run_dir / "predictions.jsonl").values())
    rows = [row for row in rows if prediction_succeeded(row)]
    write_lock = threading.Lock()
    completed = _completed_sample_ids(run_dir)
    pending = [row for row in rows if row.get("sample_id") not in completed]
    newly_succeeded: set[str] = set()

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
            if result.success and result.output is not None:
                newly_succeeded.add(row.get("sample_id"))

    _run_pool(_process, pending, concurrency)
    n_success = len(completed | newly_succeeded)
    if n_success == len(rows):
        print(f"[done] {run_id} / {task}: parsed {n_success}/{len(rows)} rows from "
              f"{source_run_dir} with {llm_name} -> {run_dir}")
    else:
        print(f"[incomplete] {run_id} / {task}: parsed {n_success}/{len(rows)} rows from "
              f"{source_run_dir}; rerun the same command to retry failures -> {run_dir}")
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
    record = {
        "run_id": run_id, "task": task, "model": model_name, "sample_id": sample_id,
        "prediction": result.output if result.success else None,
        "success": result.success,
        "finish_reason": ar.finish_reason if ar is not None else None,
        "raw_output": result.raw_outputs_per_try[-1] if result.raw_outputs_per_try else None,
    }
    if expected is not None:
        record["expected"] = expected
    if extra:
        record.update(extra)
    append_jsonl(run_dir / "predictions.jsonl", record)
    append_jsonl(run_dir / "metrics.jsonl", dataclasses.asdict(metrics))
