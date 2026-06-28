"""Shared collection loop used by every scripts/data_collection/run_*.py.

Two modes, dispatched by prompt_type:
  * VLM tasks (closed_binary / open_detection / multilabel_classification):
        iterate dataset samples, send video + prompt to a VLM.
  * freetext_parser (p6): iterate a prior p2 run's outputs, fill the p6 prompt,
        send text to an LLM.

Outputs go to runs/raw/{task}/{vlm}[/{llm}]/{run_id}/ with predictions.jsonl,
metrics.jsonl, run_config.json and per-call artifacts. See docs/ARCHITECTURE.md.

NOTE: this is the scaffold wiring. The provider adapters and dataset/media
helpers are borrowed from the previous codebase; the seams marked TODO are where
live-run details (contact-sheet media, p2-source selection) may need tuning once
data collection is exercised end to end.
"""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import client as _client
from . import prompts as _prompts
from . import schemas as _schemas
from .adapters import get_adapter
from .io_utils import append_jsonl, atomic_write_json, read_json, safe_name


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
    models = _load_yaml(models_path).get("models", {})
    defaults = _load_yaml(defaults_path)
    costs = _client.load_model_costs(costs_path)
    return {"models": models, "defaults": defaults, "model_costs": costs}


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _new_run_dir(task: str, *parts: str, runs_root: str | Path = "runs") -> Path:
    rid = _run_id()
    d = Path(runs_root) / "raw" / task / "/".join(safe_name(p) for p in parts) / rid
    (d / "artifacts").mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- #
# VLM collection (p1 / p2 / p3)
# --------------------------------------------------------------------------- #
def collect(
    task: str,
    model_name: str,
    config: dict,
    *,
    limit: int | None = None,
    runs_root: str | Path = "runs",
) -> Path:
    from .dataset import filter_samples, load_samples, select_videos
    from .media import maybe_transcode_videos

    ptype = _prompts.prompt_type_of(task)
    if ptype == "freetext_parser":
        raise ValueError("Use run_parser() for the freetext_parser task.")

    model_cfg = dict(config["models"][model_name])
    adapter = get_adapter(model_cfg["adapter"], model_cfg)
    cost_entry = config["model_costs"].get(model_cfg.get("provider_model_id"))
    defaults = config["defaults"]
    media_cfg = defaults.get("media", {})
    call_cfg = defaults.get("call", {})

    prompt_text = _prompts.load_prompt(task)  # protocol is baked into the .md
    # parse_fn: structured tasks → JSON; open_detection is freeform but still JSON-shaped
    parse_fn = _client.parse_first_json

    meta_path = Path(defaults["dataset"]["metadata_path"])
    samples = filter_samples(load_samples(meta_path), None)
    if limit:
        samples = samples[:limit]
    dataset_root = Path(read_json(meta_path)["dataset"]["local_root"])

    run_dir = _new_run_dir(task, model_name, runs_root=runs_root)
    atomic_write_json(run_dir / "run_config.json",
                      {"task": task, "model": model_name, "model_cfg": model_cfg,
                       "defaults": defaults})

    for sample in samples:
        videos = select_videos(sample, dataset_root, media_cfg.get("camera_views", []),
                               int(media_cfg.get("max_videos_per_sample", 0)))
        videos = maybe_transcode_videos(videos, run_dir / "media_cache" / sample.sample_id, media_cfg)
        media = [{"type": "video", "path": str(v["path"])} for v in videos]  # TODO: contact-sheet mode

        result, ar = _client.call_with_retries(
            adapter, prompt=prompt_text, media=media,
            request_metadata={"task": task, "model": model_name, "sample_id": sample.sample_id},
            model_name=model_name, cost_entry=cost_entry,
            max_retries=int(call_cfg.get("max_retries", 5)), parse_fn=parse_fn,
        )
        _write_record(run_dir, task, model_name, sample.sample_id, result, ar)

    print(f"[done] {task} / {model_name}: wrote {run_dir}")
    return run_dir


# --------------------------------------------------------------------------- #
# p6 parser (text LLM over a prior p2 run)
# --------------------------------------------------------------------------- #
def run_parser(
    task: str,
    llm_name: str,
    p2_run_dir: str | Path,
    config: dict,
    *,
    runs_root: str | Path = "runs",
) -> Path:
    """Fill the p6 prompt from each p2 prediction and call a text LLM."""
    if _prompts.prompt_type_of(task) != "freetext_parser":
        raise ValueError(f"run_parser expects a *_freetext_parser task, got {task}")

    p2_run_dir = Path(p2_run_dir)
    vlm_name = p2_run_dir.parent.name  # runs/raw/{op}_open_detection/{vlm}/{run_id}
    model_cfg = dict(config["models"][llm_name])
    adapter = get_adapter(model_cfg["adapter"], model_cfg)
    cost_entry = config["model_costs"].get(model_cfg.get("provider_model_id"))
    call_cfg = config["defaults"].get("call", {})
    template = _prompts.load_prompt_file(_prompts.get_prompt_path(task))

    run_dir = _new_run_dir(task, vlm_name, llm_name, runs_root=runs_root)
    atomic_write_json(run_dir / "run_config.json",
                      {"task": task, "vlm": vlm_name, "llm": llm_name,
                       "p2_run_dir": str(p2_run_dir), "model_cfg": model_cfg})

    for line in (p2_run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        p2 = row.get("prediction") or {}
        # reasoning is intentionally NOT passed to the parser (see p6 prompt).
        prompt_text = _prompts.fill_in_prompt(template, {
            "error_present": json.dumps(p2.get("error_present")),
            "observed_errors": json.dumps(p2.get("observed_errors") or []),
            "confidence": json.dumps(p2.get("confidence")),
        })
        result, ar = _client.call_with_retries(
            adapter, prompt=prompt_text, media=[],
            request_metadata={"task": task, "vlm": vlm_name, "llm": llm_name,
                              "sample_id": row.get("sample_id")},
            model_name=llm_name, cost_entry=cost_entry,
            max_retries=int(call_cfg.get("max_retries", 5)), parse_fn=_client.parse_first_json,
        )
        _write_record(run_dir, task, llm_name, row.get("sample_id"), result, ar,
                      extra={"source_vlm": vlm_name})

    print(f"[done] {task}: parsed {p2_run_dir} with {llm_name} -> {run_dir}")
    return run_dir


# --------------------------------------------------------------------------- #
# Shared record writer
# --------------------------------------------------------------------------- #
def _write_record(run_dir: Path, task: str, model_name: str, sample_id: str,
                  result: _client.CallResult, ar, extra: dict | None = None) -> None:
    runtime = ar.latency_s if ar is not None else 0.0
    metrics = _client.CallMetrics.build(result, model=model_name, run_id=run_dir.name,
                                        runtime_s=runtime or 0.0)
    rid = safe_name(f"{model_name}__{sample_id}")
    if ar is not None:
        atomic_write_json(run_dir / "artifacts" / f"{rid}.json",
                          {"raw_text": ar.raw_text, "usage": ar.usage,
                           "finish_reason": ar.finish_reason})
    record = {
        "task": task, "model": model_name, "sample_id": sample_id,
        "prediction": result.output if result.success else None,
        "success": result.success,
        "raw_output": result.raw_outputs_per_try[-1] if result.raw_outputs_per_try else None,
    }
    if extra:
        record.update(extra)
    append_jsonl(run_dir / "predictions.jsonl", record)
    append_jsonl(run_dir / "metrics.jsonl", dataclasses.asdict(metrics))
